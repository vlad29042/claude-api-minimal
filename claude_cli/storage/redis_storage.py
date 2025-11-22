"""Redis-based session storage with SessionStorage interface compatibility."""

import asyncio
import json
import logging
from typing import Optional, List, Callable, Awaitable, TypeVar

T = TypeVar('T')
from datetime import timedelta

try:
    import redis.asyncio as redis
    from redis.asyncio.connection import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    ConnectionPool = None

# Import SessionStorage base class and ClaudeSession
from ..session import SessionStorage, ClaudeSession

logger = logging.getLogger(__name__)


class RedisSessionStorage(SessionStorage):
    """
    Redis-based session storage implementing SessionStorage interface.

    Features:
    - Full SessionStorage interface compatibility
    - Async/await API
    - Connection pooling with configurable pool size
    - Automatic reconnection on connection failures
    - Graceful degradation to in-memory storage
    - Configurable TTL for session data
    - User and global session indexing
    - Comprehensive logging
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 10,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        default_ttl: int = 86400,  # 24 hours default
        key_prefix: str = "claude_session:",
        enable_fallback: bool = True,
    ):
        """
        Initialize Redis session storage.

        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            password: Redis password (optional)
            max_connections: Maximum number of connections in pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connection timeout in seconds
            default_ttl: Default TTL for session data in seconds (24h)
            key_prefix: Prefix for all Redis keys
            enable_fallback: Enable fallback to in-memory storage on Redis failure
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.enable_fallback = enable_fallback

        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._is_connected = False
        self._lock = asyncio.Lock()

        # Fallback in-memory storage
        from ..session import InMemorySessionStorage
        self._fallback = InMemorySessionStorage()

        # Check if redis is available
        if not REDIS_AVAILABLE:
            logger.warning(
                "redis package not installed. Install with: pip install 'redis[hiredis]>=5.0.0'"
            )
            if not enable_fallback:
                raise ImportError("redis package required but not installed")

    async def _ensure_connection(self) -> bool:
        """
        Ensure connection to Redis server.

        Returns:
            True if connected successfully, False if using fallback
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using fallback storage")
            return False

        async with self._lock:
            if self._is_connected and self._client:
                try:
                    await self._client.ping()
                    return True
                except Exception:
                    self._is_connected = False

            try:
                logger.info(
                    f"Connecting to Redis at {self.host}:{self.port} (db={self.db})"
                )

                # Create connection pool
                self._pool = ConnectionPool(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    max_connections=self.max_connections,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout,
                    decode_responses=True,
                )

                # Create Redis client
                self._client = redis.Redis(connection_pool=self._pool)

                # Test connection
                await self._client.ping()

                self._is_connected = True
                logger.info("Successfully connected to Redis")
                return True

            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._is_connected = False

                if self.enable_fallback:
                    logger.info("Using in-memory fallback storage")
                    return False
                else:
                    raise

    def _make_session_key(self, session_id: str) -> str:
        """Generate Redis key for session data."""
        return f"{self.key_prefix}{session_id}"

    def _make_user_index_key(self, user_id: int) -> str:
        """Generate Redis key for user's session index."""
        return f"{self.key_prefix}user:{user_id}:sessions"

    def _make_global_index_key(self) -> str:
        """Generate Redis key for global session index."""
        return f"{self.key_prefix}all_sessions"

    # ==================== SessionStorage Interface ====================

    async def _execute_with_fallback(
        self,
        operation_name: str,
        redis_operation: Callable[[], Awaitable[T]],
        fallback_operation: Callable[[], Awaitable[T]]
    ) -> Optional[T]:
        """Execute Redis operation with automatic fallback on failure.

        Args:
            operation_name: Name of operation for logging
            redis_operation: Async callable for Redis operation
            fallback_operation: Async callable for fallback operation

        Returns:
            Result from redis_operation or fallback_operation
        """
        # Try Redis first
        if await self._ensure_connection():
            try:
                result = await redis_operation()
                logger.debug(f"{operation_name} completed in Redis")
                return result
            except Exception as e:
                logger.error(f"Failed to {operation_name} in Redis: {e}")
                self._is_connected = False

        # Fallback to in-memory
        if self.enable_fallback:
            result = await fallback_operation()
            logger.debug(f"{operation_name} completed in fallback storage")
            return result

        return None

    async def save_session(self, session: ClaudeSession) -> None:
        """
        Save session to Redis storage.

        Args:
            session: ClaudeSession object to save
        """
        session_data = json.dumps(session.to_dict())
        session_key = self._make_session_key(session.session_id)
        user_index_key = self._make_user_index_key(session.user_id)
        global_index_key = self._make_global_index_key()

        async def redis_save():
            # Use pipeline for atomic operations
            async with self._client.pipeline(transaction=True) as pipe:
                # Save session data with TTL
                pipe.setex(
                    session_key,
                    timedelta(seconds=self.default_ttl),
                    session_data,
                )

                # Add to user index
                pipe.sadd(user_index_key, session.session_id)
                pipe.expire(user_index_key, timedelta(seconds=self.default_ttl))

                # Add to global index
                pipe.sadd(global_index_key, session.session_id)

                await pipe.execute()

        async def fallback_save():
            await self._fallback.save_session(session)

        await self._execute_with_fallback(
            f"save_session {session.session_id}",
            redis_save,
            fallback_save
        )

    async def load_session(self, session_id: str) -> Optional[ClaudeSession]:
        """
        Load session from Redis storage.

        Args:
            session_id: Session ID to load

        Returns:
            ClaudeSession object or None if not found
        """
        session_key = self._make_session_key(session_id)

        async def redis_load():
            session_data = await self._client.get(session_key)
            if session_data:
                session_dict = json.loads(session_data)
                return ClaudeSession.from_dict(session_dict)
            return None

        async def fallback_load():
            return await self._fallback.load_session(session_id)

        return await self._execute_with_fallback(
            f"load_session {session_id}",
            redis_load,
            fallback_load
        )

    async def delete_session(self, session_id: str) -> None:
        """
        Delete session from Redis storage.

        Args:
            session_id: Session ID to delete
        """
        # First load session to get user_id for index cleanup
        session = await self.load_session(session_id)

        session_key = self._make_session_key(session_id)
        global_index_key = self._make_global_index_key()

        async def redis_delete():
            async with self._client.pipeline(transaction=True) as pipe:
                # Delete session data
                pipe.delete(session_key)

                # Remove from user index if we have user_id
                if session:
                    user_index_key = self._make_user_index_key(session.user_id)
                    pipe.srem(user_index_key, session_id)

                # Remove from global index
                pipe.srem(global_index_key, session_id)

                await pipe.execute()

            # Also delete from fallback
            if self.enable_fallback:
                await self._fallback.delete_session(session_id)

        async def fallback_delete():
            await self._fallback.delete_session(session_id)

        await self._execute_with_fallback(
            f"delete_session {session_id}",
            redis_delete,
            fallback_delete
        )

    async def get_user_sessions(self, user_id: int) -> List[ClaudeSession]:
        """
        Get all sessions for a specific user.

        Args:
            user_id: User ID to get sessions for

        Returns:
            List of ClaudeSession objects for the user
        """
        user_index_key = self._make_user_index_key(user_id)

        # Try Redis first
        if await self._ensure_connection():
            try:
                # Get session IDs from user index
                session_ids = await self._client.smembers(user_index_key)

                if session_ids:
                    # Load all sessions
                    sessions = []
                    for session_id in session_ids:
                        session = await self.load_session(session_id)
                        if session:
                            sessions.append(session)
                        else:
                            # Clean up stale index entry
                            await self._client.srem(user_index_key, session_id)

                    logger.debug(f"Loaded {len(sessions)} sessions for user {user_id} from Redis")
                    return sessions

                return []

            except Exception as e:
                logger.error(f"Failed to get user sessions from Redis: {e}")
                self._is_connected = False

        # Fallback to in-memory
        if self.enable_fallback:
            sessions = await self._fallback.get_user_sessions(user_id)
            logger.debug(f"Loaded {len(sessions)} sessions for user {user_id} from fallback storage")
            return sessions

        return []

    async def get_all_sessions(self) -> List[ClaudeSession]:
        """
        Get all sessions from storage.

        Returns:
            List of all ClaudeSession objects
        """
        global_index_key = self._make_global_index_key()

        # Try Redis first
        if await self._ensure_connection():
            try:
                # Get all session IDs from global index
                session_ids = await self._client.smembers(global_index_key)

                if session_ids:
                    # Load all sessions
                    sessions = []
                    for session_id in session_ids:
                        session = await self.load_session(session_id)
                        if session:
                            sessions.append(session)
                        else:
                            # Clean up stale index entry
                            await self._client.srem(global_index_key, session_id)

                    logger.debug(f"Loaded {len(sessions)} total sessions from Redis")
                    return sessions

                return []

            except Exception as e:
                logger.error(f"Failed to get all sessions from Redis: {e}")
                self._is_connected = False

        # Fallback to in-memory
        if self.enable_fallback:
            sessions = await self._fallback.get_all_sessions()
            logger.debug(f"Loaded {len(sessions)} total sessions from fallback storage")
            return sessions

        return []

    # ==================== Additional Methods ====================

    async def disconnect(self) -> None:
        """Close Redis connection and cleanup resources."""
        async with self._lock:
            if self._client:
                try:
                    await self._client.aclose()
                    logger.info("Redis connection closed")
                except Exception as e:
                    logger.error(f"Error closing Redis connection: {e}")
                finally:
                    self._client = None

            if self._pool:
                try:
                    await self._pool.aclose()
                except Exception as e:
                    logger.error(f"Error closing connection pool: {e}")
                finally:
                    self._pool = None

            self._is_connected = False

    async def clear_all(self) -> int:
        """
        Clear all session data with the configured prefix.

        Returns:
            Number of sessions deleted
        """
        # Try Redis first
        if await self._ensure_connection():
            try:
                # Use SCAN to find and delete all keys with prefix
                pattern = f"{self.key_prefix}*"
                deleted_count = 0

                async for key in self._client.scan_iter(match=pattern, count=100):
                    await self._client.delete(key)
                    deleted_count += 1

                logger.info(f"Cleared {deleted_count} keys from Redis")

                # Also clear fallback
                if self.enable_fallback:
                    self._fallback.sessions.clear()

                return deleted_count

            except Exception as e:
                logger.error(f"Failed to clear Redis storage: {e}")
                self._is_connected = False

        # Fallback to in-memory
        if self.enable_fallback:
            count = len(self._fallback.sessions)
            self._fallback.sessions.clear()
            logger.info(f"Cleared {count} sessions from fallback storage")
            return count

        return 0

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_connection()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
