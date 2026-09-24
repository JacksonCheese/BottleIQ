import pytest
from sqlalchemy import create_engine

from bottleiq.migrations import check_migrations


def test_unmigrated_database_reports_required_action():
    engine = create_engine("sqlite://")
    with pytest.raises(RuntimeError, match="Run 'make migrate'") as error:
        check_migrations(engine)
    assert "installed: none" in str(error.value)
