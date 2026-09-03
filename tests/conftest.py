"""Pytest configuration and fixtures."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from asynccraft.kernel.models import Base
from asynccraft.kernel.tools import ToolRegistry, register_tool
from asynccraft.skins.ops_dispatch.tools import NotifyDispatcherTool
from asynccraft.skins.deal_flow.tools import CreateCRMDealTool


@pytest.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def tool_registry():
    """Create a tool registry with test tools."""
    registry = ToolRegistry()
    registry.register(NotifyDispatcherTool())
    registry.register(CreateCRMDealTool())
    return registry
