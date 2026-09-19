import asyncio, os, socket, logging
from app.config import settings
from app import main
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta
from app.models import BackupJob, Payment, WorkerState, Job, TrialGrant, User, Subscription, Plan, ProvisioningOperation
from redis.asyncio import Redis

logger=logging.getLogger("vpnshop.worker")

async def job_worker():
    worker_id=os.getenv("WORKER_ID") or f"{settings.worker_role}:{socket.gethostname()}:{os.getpid()}"
    while True:
        try:
            async with AsyncSession(main.engine,expire_on_commit=False) as db:
                now=datetime.utcnow()
                # Recover jobs abandoned by a dead worker, but never steal a fresh lease.
                await db.execute(update(Job).where(Job.status=="processing", Job.locked_at.is_not(None), Job.locked_at < now-timedelta(minutes=10)).values(status="queued", locked_at=None, worker_id=None, next_retry_at=now))
                await db.commit()
                job=(await db.execute(select(Job).where(Job.status=="queued", (Job.next_retry_at.is_(None)) | (Job.next_retry_at<=now)).order_by(Job.id).with_for_update(skip_locked=True).limit(1))).scalar_one_or_none()
                if job:
                    job.status="processing"; job.locked_at=now; job.worker_id=worker_id; job.attempts=(job.attempts or 0)+1
                    await db.commit()
                    if job.kind=="trial":
                        trial_id=int((job.payload or {}).get("trial_id",0))
                        try:
                            async with AsyncSession(main.engine,expire_on_commit=False) as edb:
                                trial=await edb.get(TrialGrant,trial_id)
                                if not trial: raise RuntimeError("Trial not found")
                                user=await edb.get(User,trial.user_id); plan=await edb.get(Plan,trial.plan_id)
                                if not user or not plan: raise RuntimeError("Trial references missing user/plan")
                                user_lock,user_token=await main._acquire_user_fulfillment_lock(user.id,ttl=900)
                                try:
                                    user=(await edb.execute(select(User).where(User.id==user.id).with_for_update())).scalar_one()
                                    if user.deleted_at is not None:
                                        trial.status="cancelled"
                                        await edb.commit()
                                        continue
                                    sub=(await edb.execute(select(Subscription).where(Subscription.user_id==user.id).with_for_update())).scalar_one_or_none()
                                    now=datetime.utcnow(); rw=main.RemnawaveClient()
                                    if sub and sub.remnawave_uuid:
                                        remote_before=await rw.get_user(sub.remnawave_uuid)
                                        remote_status=str(remote_before.get("status") or remote_before.get("state") or "").lower() if isinstance(remote_before,dict) else ""
                                        if remote_status in {"disabled","blocked","inactive"}:
                                            await rw.enable_user(sub.remnawave_uuid)
                                        remote_expiry=await rw.get_expiry(sub.remnawave_uuid)
                                        # Persist a fixed target on the TrialGrant before the external
                                        # call. A retry after a lost response must not add another full
                                        # trial period to an already successful remote extension.
                                        before=trial.expected_before_expires_at
                                        after=trial.expected_after_expires_at
                                        if before is None or after is None:
                                            before=max(sub.expires_at or now, remote_expiry or now, now)
                                            after=before+timedelta(days=trial.days)
                                            trial.expected_before_expires_at=before; trial.expected_after_expires_at=after
                                            await edb.commit()
                                        await rw.update_entitlements(sub.remnawave_uuid,trial.traffic_limit_gb_snapshot,trial.remnawave_profile_id_snapshot)
                                        extension=await rw.extend_idempotent(sub.remnawave_uuid,trial.days,before,after)
                                        verified_expiry=extension.get("expires_at") if isinstance(extension,dict) else None
                                        sub.expires_at=max(after,verified_expiry or after); sub.plan_id=plan.id; sub.traffic_limit_gb_snapshot=trial.traffic_limit_gb_snapshot; sub.device_limit_snapshot=trial.device_limit_snapshot; sub.remnawave_profile_id_snapshot=trial.remnawave_profile_id_snapshot
                                    else:
                                        username=f"user_{user.id}"; existing=None
                                        try: existing=await rw.get_user_by_username(username)
                                        except Exception: existing=None
                                        expected=trial.expires_at or (now+timedelta(days=trial.days))
                                        if existing and existing.get("id"):
                                            data=existing
                                            remote_id=str(data.get("id"))
                                            remote_status=str(data.get("status") or data.get("state") or "").lower()
                                            if remote_status in {"disabled","blocked","inactive"}:
                                                await rw.enable_user(remote_id)
                                            # Trial entitlements are immutable snapshots. Do not let a
                                            # later admin edit to Plan change the traffic/profile of a
                                            # trial that was already granted.
                                            await rw.update_entitlements(remote_id,trial.traffic_limit_gb_snapshot,trial.remnawave_profile_id_snapshot)
                                            remote_expiry=await rw.get_expiry(remote_id)
                                            target_expiry=max(expected, remote_expiry or expected)
                                            if not remote_expiry or remote_expiry < target_expiry:
                                                before_remote=remote_expiry or now
                                                extension_seconds=(target_expiry-max(before_remote,now)).total_seconds()
                                                extension_days=max(1, int((extension_seconds + 86399) // 86400))
                                                await rw.extend_idempotent(remote_id,extension_days,before_remote,target_expiry)
                                                data=await rw.get_user(remote_id)
                                        else:
                                            traffic=trial.traffic_limit_gb_snapshot*1024**3 if trial.traffic_limit_gb_snapshot else 0
                                            data=await rw.create_user(username,expected,traffic,active_internal_squads=[trial.remnawave_profile_id_snapshot] if trial.remnawave_profile_id_snapshot else None,telegram_id=user.telegram_id)
                                        if not sub: sub=Subscription(user_id=user.id,plan_id=plan.id); edb.add(sub)
                                        sub.plan_id=plan.id; sub.remnawave_uuid=str(data.get("id"))
                                        # Never move the local expiry backwards if a prior
                                        # successful remote operation already extended the user.
                                        remote_final=await rw.get_expiry(str(data.get("id")))
                                        sub.expires_at=max(expected, remote_final or expected)
                                        sub.traffic_limit_gb_snapshot=trial.traffic_limit_gb_snapshot
                                        sub.device_limit_snapshot=trial.device_limit_snapshot
                                        sub.remnawave_profile_id_snapshot=trial.remnawave_profile_id_snapshot
                                        sub.subscription_url=data.get("subscriptionUrl") or data.get("subscription_url")
                                    trial.status="completed"; await edb.commit()
                                finally:
                                    await main._release_payment_side_effect_lock(user_lock,user_token)
                            async with AsyncSession(main.engine,expire_on_commit=False) as edb:
                                j=await edb.get(Job,job.id); j.status="completed"; j.completed_at=datetime.utcnow(); j.locked_at=None; j.worker_id=None; await edb.commit()
                        except Exception as exc:
                            logger.exception("trial job %s failed",job.id)
                            async with AsyncSession(main.engine,expire_on_commit=False) as edb:
                                j=await edb.get(Job,job.id)
                                if j: j.status="failed" if j.attempts>=j.max_attempts else "queued"; j.error=str(exc)[:2000]; j.locked_at=None; j.worker_id=None; j.next_retry_at=datetime.utcnow()+timedelta(seconds=min(3600,60*(2**max(0,j.attempts-1)))); await edb.commit()
                    elif job.kind=="fulfillment":
                        payment_id=int((job.payload or {}).get("payment_id",0))
                        if not payment_id: raise RuntimeError("Fulfillment job has no payment_id")
                        try:
                            await main.fulfill(payment_id,db)
                        except Exception as exc:
                            logger.exception("fulfillment job %s failed",job.id)
                            async with AsyncSession(main.engine,expire_on_commit=False) as edb:
                                j=await edb.get(Job,job.id)
                                if j and j.status=="processing":
                                    j.status="failed" if j.attempts>=j.max_attempts else "queued"; j.error=str(exc)[:2000]; j.locked_at=None; j.worker_id=None; j.next_retry_at=datetime.utcnow()+timedelta(seconds=min(3600,60*(2**max(0,j.attempts-1))))
                                    await edb.commit()
                    else:
                        async with AsyncSession(main.engine,expire_on_commit=False) as edb:
                            j=await edb.get(Job,job.id)
                            if j: j.status="failed"; j.error=f"Unsupported job kind: {job.kind}"; j.locked_at=None; j.worker_id=None; await edb.commit()
            await asyncio.sleep(1)
        except Exception:
            logger.exception("job worker loop failure")
            await asyncio.sleep(2)

async def health_alert_worker():
    last=None
    while True:
        try:
            async with AsyncSession(main.engine,expire_on_commit=False) as db:
                failed=int((await db.execute(select(__import__('sqlalchemy').func.count()).select_from(Payment).where(Payment.fulfillment_status=='failed',Payment.created_at>=datetime.utcnow()-timedelta(hours=1)))).scalar() or 0)
                backup=(await db.execute(select(BackupJob).where(BackupJob.status=='completed').order_by(BackupJob.created_at.desc()).limit(1))).scalar_one_or_none()
                state=(failed, bool(backup and backup.created_at>=datetime.utcnow()-timedelta(hours=25)))
                if last is not None and state != last:
                    if failed >= 5: await main.send_alert(f"High fulfillment failures in last hour: {failed}")
                    if not state[1]: await main.send_alert("No successful backup in the last 25 hours")
                last=state
        except Exception:
            logger.exception("health alert worker failure")
        await asyncio.sleep(300)

async def worker_heartbeat():
    worker_id=os.getenv("WORKER_ID") or f"{settings.worker_role}:{socket.gethostname()}:{os.getpid()}"
    while True:
        try:
            now=datetime.utcnow()
            await main.redis_client.set(f"worker:heartbeat:{worker_id}", now.isoformat(), ex=90)
            async with AsyncSession(main.engine,expire_on_commit=False) as db:
                row=(await db.execute(select(WorkerState).where(WorkerState.worker_id==worker_id))).scalar_one_or_none()
                if not row:
                    row=WorkerState(worker_id=worker_id,role=settings.worker_role,status="online",last_seen_at=now); db.add(row)
                else:
                    row.status="online"; row.role=settings.worker_role; row.last_seen_at=now
                await db.commit()
        except Exception:
            logger.exception("worker heartbeat failure")
        await asyncio.sleep(30)

async def main_worker():
    main.redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    await main.redis_client.ping()
    await asyncio.gather(worker_heartbeat(), health_alert_worker(), job_worker(),
        main.backup_scheduler(),
        main.fulfillment_retry_scheduler(),
        main.expiry_notification_scheduler(),
        main.reconciliation_scheduler(),
        main.auto_renew_scheduler(),
        main.refund_revoke_scheduler(),
        main.subscription_lifecycle_scheduler(),
    )

if __name__ == "__main__":
    asyncio.run(main_worker())
