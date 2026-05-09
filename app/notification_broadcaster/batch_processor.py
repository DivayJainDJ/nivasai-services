"""Batch notification processor."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from app.notification_broadcaster.fcm_sender import FCMSender
from app.notification_broadcaster.schemas import BatchSendResult, NotificationPayload
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class BatchProcessor:
    """Process notifications in batches."""

    def __init__(self):
        """Initialize batch processor."""
        self.fcm_sender = FCMSender()
        self.batch_size = int(os.getenv("FCM_BATCH_SIZE", "500"))
        self.max_workers = int(os.getenv("FCM_MAX_WORKERS", "5"))

    def process_batch(
        self,
        tokens: List[str],
        payload: NotificationPayload,
    ) -> BatchSendResult:
        """
        Process notification batch.
        
        Args:
            tokens: List of FCM tokens
            payload: Notification payload
        
        Returns:
            Aggregated BatchSendResult
        """
        try:
            if not tokens:
                logger.warning("no_tokens_to_process")
                return BatchSendResult()
            
            logger.info(
                "batch_processing_started",
                total_tokens=len(tokens),
                batch_size=self.batch_size,
            )
            
            # Chunk tokens into batches
            chunks = self._chunk_tokens(tokens, self.batch_size)
            
            logger.info("tokens_chunked", chunk_count=len(chunks))
            
            # Process chunks
            if len(chunks) == 1:
                # Single chunk - process directly
                result = self.fcm_sender.send_notification(chunks[0], payload)
            else:
                # Multiple chunks - process in parallel
                result = self._process_parallel(chunks, payload)
            
            logger.info(
                "batch_processing_completed",
                success=result.successCount,
                failure=result.failureCount,
                invalid=len(result.invalidTokens),
            )
            
            return result
        
        except Exception as exc:
            logger.error("batch_processing_failed", error=str(exc))
            return BatchSendResult(
                failureCount=len(tokens),
                errors=[str(exc)],
            )

    def _chunk_tokens(self, tokens: List[str], chunk_size: int) -> List[List[str]]:
        """
        Split tokens into chunks.
        
        Args:
            tokens: List of tokens
            chunk_size: Size of each chunk
        
        Returns:
            List of token chunks
        """
        chunks = []
        for i in range(0, len(tokens), chunk_size):
            chunk = tokens[i:i + chunk_size]
            chunks.append(chunk)
        
        return chunks

    def _process_parallel(
        self,
        chunks: List[List[str]],
        payload: NotificationPayload,
    ) -> BatchSendResult:
        """
        Process chunks in parallel.
        
        Args:
            chunks: List of token chunks
            payload: Notification payload
        
        Returns:
            Aggregated BatchSendResult
        """
        aggregated_result = BatchSendResult()
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all chunks
                futures = {
                    executor.submit(
                        self.fcm_sender.send_notification,
                        chunk,
                        payload,
                    ): idx
                    for idx, chunk in enumerate(chunks)
                }
                
                # Collect results
                for future in as_completed(futures):
                    chunk_idx = futures[future]
                    try:
                        result = future.result()
                        
                        # Aggregate results
                        aggregated_result.successCount += result.successCount
                        aggregated_result.failureCount += result.failureCount
                        aggregated_result.invalidTokens.extend(result.invalidTokens)
                        aggregated_result.errors.extend(result.errors)
                        
                        logger.info(
                            "chunk_completed",
                            chunk_idx=chunk_idx,
                            success=result.successCount,
                            failure=result.failureCount,
                        )
                    
                    except Exception as exc:
                        logger.error("chunk_processing_failed", chunk_idx=chunk_idx, error=str(exc))
                        aggregated_result.failureCount += len(chunks[chunk_idx])
                        aggregated_result.errors.append(f"Chunk {chunk_idx}: {str(exc)}")
            
            return aggregated_result
        
        except Exception as exc:
            logger.error("parallel_processing_failed", error=str(exc))
            # Count all tokens as failed
            total_tokens = sum(len(chunk) for chunk in chunks)
            return BatchSendResult(
                failureCount=total_tokens,
                errors=[str(exc)],
            )

    def process_large_batch(
        self,
        tokens: List[str],
        payload: NotificationPayload,
        enable_parallel: bool = True,
    ) -> BatchSendResult:
        """
        Process large batch with optimizations.
        
        Args:
            tokens: List of FCM tokens
            payload: Notification payload
            enable_parallel: Enable parallel processing
        
        Returns:
            BatchSendResult
        """
        try:
            token_count = len(tokens)
            
            logger.info(
                "large_batch_started",
                token_count=token_count,
                parallel_enabled=enable_parallel,
            )
            
            # For very large batches, use parallel processing
            if enable_parallel and token_count > self.batch_size:
                chunks = self._chunk_tokens(tokens, self.batch_size)
                result = self._process_parallel(chunks, payload)
            else:
                # Sequential processing
                result = self.fcm_sender.send_notification(tokens, payload)
            
            logger.info(
                "large_batch_completed",
                token_count=token_count,
                success=result.successCount,
                failure=result.failureCount,
            )
            
            return result
        
        except Exception as exc:
            logger.error("large_batch_failed", error=str(exc))
            return BatchSendResult(
                failureCount=len(tokens),
                errors=[str(exc)],
            )

    def estimate_batch_time(self, token_count: int) -> float:
        """
        Estimate processing time for batch.
        
        Args:
            token_count: Number of tokens
        
        Returns:
            Estimated time in seconds
        """
        # Rough estimate: 100ms per 100 tokens
        chunks = (token_count + self.batch_size - 1) // self.batch_size
        
        if chunks <= self.max_workers:
            # Parallel processing
            estimated_time = (chunks * 0.1)
        else:
            # Sequential batches
            estimated_time = (chunks * 0.1) / self.max_workers
        
        logger.info(
            "batch_time_estimated",
            token_count=token_count,
            chunks=chunks,
            estimated_seconds=estimated_time,
        )
        
        return estimated_time

    def get_batch_statistics(self, result: BatchSendResult) -> dict:
        """
        Get batch processing statistics.
        
        Args:
            result: BatchSendResult
        
        Returns:
            Statistics dict
        """
        total = result.successCount + result.failureCount
        success_rate = (result.successCount / total * 100) if total > 0 else 0
        
        stats = {
            "total": total,
            "success": result.successCount,
            "failure": result.failureCount,
            "invalid_tokens": len(result.invalidTokens),
            "success_rate": round(success_rate, 2),
            "error_count": len(result.errors),
        }
        
        logger.info("batch_statistics", **stats)
        
        return stats
