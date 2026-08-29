import pandas as pd
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.agent.manager import AgentManager
from backend.app.database import Base
from backend.app.models import (
    ChatSession,
    Dataset,
    User,
)

@pytest.fixture
def sample_dataframe():
    """Create a sample census-like dataframe for testing."""
    return pd.DataFrame({
        'age': [25, 30, 35, 40, 45, 50, 55, 60],
        'income': [30000, 45000, 55000, 65000, 75000, 85000, 95000, 105000],
        'education': ['HS', 'BS', 'BS', 'MS', 'MS', 'PhD', 'PhD', 'PhD'],
        'workclass': ['Private', 'Private', 'Gov', 'Private', 'Gov', 'Private', 'Self', 'Self']
    })


@pytest.fixture
def context(sample_dataframe):
    """Create context for agent manager."""
    return {
        'df': sample_dataframe,
        'dataset_id': 1,
        'dataset_name': 'test_census.csv',
        'columns': sample_dataframe.columns.tolist(),
        'shape': sample_dataframe.shape,
        'dtypes': sample_dataframe.dtypes.astype(str).to_dict()
    }


@pytest.fixture
def agent_manager(
    tmp_path,
    monkeypatch,
    sample_dataframe,
):
    """
    AgentManager réel avec SQLite et CSV temporaires.

    Aucun PostgreSQL réel ni API LLM externe
    ne sont nécessaires pour ce test.
    """

    monkeypatch.chdir(tmp_path)

    upload_directory = (
        tmp_path
        / "uploads"
        / "user_test"
        / "session_test"
    )

    upload_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_path = (
        upload_directory
        / "test_census.csv"
    )

    sample_dataframe.to_csv(
        csv_path,
        index=False,
    )

    database_path = (
        tmp_path
        / "agent_integration.db"
    )

    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={
            "check_same_thread": False,
        },
    )

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(
        bind=engine
    )

    db = TestingSessionLocal()

    user = User(
        email="agent-test@example.com",
        hashed_password="unused-in-test",
        is_active=True,
    )

    db.add(user)
    db.flush()

    chat_session = ChatSession(
        user_id=user.id,
        title="Agent integration test",
    )

    db.add(chat_session)
    db.flush()

    dataset = Dataset(
        user_id=user.id,
        session_id=chat_session.id,
        filename="test_census.csv",
        storage_path=str(
            csv_path.resolve()
        ),
        description="Census test dataset",
    )

    db.add(dataset)
    db.commit()

    manager = AgentManager(
        session_id=chat_session.id,
        user_id=user.id,
        db=db,
    )

    manager.load_dataframe_context()

    yield manager

    db.close()

    Base.metadata.drop_all(
        bind=engine
    )

    engine.dispose()


@pytest.mark.integration
def test_describe_dataset(
    agent_manager,
):
    result = agent_manager.run_agent_turn(
        user_query="Describe the dataset",
        planner=DescribePlanner(),
    )

    assert result["answer"]

    assert "8 rows" in result["answer"]
    assert "4 columns" in result["answer"]
    assert "age" in result["answer"]
    assert "income" in result["answer"]


@pytest.mark.integration
def test_create_histogram(
    agent_manager,
):
    result = agent_manager.run_agent_turn(
        user_query="Create an age histogram",
        planner=HistogramPlanner(),
    )

    assert result["answer"]
    assert len(result["figures"]) == 1

    figure = result["figures"][0]

    assert "data" in figure
    assert len(figure["data"]) >= 1

    assert (
        figure["data"][0]["type"]
        == "histogram"
    )

    assert (
        figure["layout"]["title"]["text"]
        == "Age distribution"
    )

@pytest.mark.integration
def test_calculate_mean(
    agent_manager,
):
    result = agent_manager.run_agent_turn(
        user_query="Calculate mean age",
        planner=MeanAgePlanner(),
    )

    expected_mean = (
        25
        + 30
        + 35
        + 40
        + 45
        + 50
        + 55
        + 60
    ) / 8

    assert expected_mean == 42.5

    assert (
        "42.5"
        in result["answer"]
    )

    assert (
        agent_manager.variables[
            "mean_age"
        ]
        == pytest.approx(42.5)
    )

@pytest.mark.integration
def test_scatter_plot(
    agent_manager,
):
    result = agent_manager.run_agent_turn(
        user_query=(
            "Create a scatter plot "
            "of age versus income"
        ),
        planner=ScatterPlanner(),
    )

    assert result["answer"]
    assert len(result["figures"]) == 1

    figure = result["figures"][0]

    assert "data" in figure
    assert len(figure["data"]) >= 1

    trace = figure["data"][0]

    assert trace["type"] == "scatter"

    assert (
        figure["layout"]["title"]["text"]
        == "Age vs income"
    )


@pytest.mark.persistence
def test_session_persistence(
    agent_manager,
):
    """
    Un nouvel AgentManager doit retrouver
    la conversation enregistrée par le précédent.
    """

    user_id = agent_manager.user_id
    session_id = agent_manager.session_id

    # Premier AgentManager :
    # exécution réelle d'un tour LangGraph.
    result = agent_manager.run_agent_turn(
        user_query="Calculate mean age",
        planner=MeanAgePlanner(),
    )

    assert "42.5" in result["answer"]

    # On conserve l'engine avant de fermer
    # complètement la session SQLAlchemy.
    engine = agent_manager.db.get_bind()

    agent_manager.db.close()

    RestartSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    restarted_db = RestartSessionLocal()

    try:
        # Nouvelle instance = simulation
        # d'un redémarrage du processus.
        restarted_manager = AgentManager(
            session_id=session_id,
            user_id=user_id,
            db=restarted_db,
        )

        history = (
            restarted_manager.load_history()
        )

        assert len(history) >= 2

        assert any(
            message["role"] == "user"
            and message["content"]
            == "Calculate mean age"
            for message in history
        )

        assert any(
            message["role"] == "assistant"
            and "42.5" in message["content"]
            for message in history
        )

    finally:
        restarted_db.close()

@pytest.mark.security
def test_code_execution_sandbox(
    agent_manager,
):
    """
    Même via AgentManager, du code Python
    interdit doit être rejeté avant exec().
    """

    malicious_attempts = [
        "__import__('os').system('echo HACKED')",
        "open('/etc/passwd', 'r').read()",
        "__import__('subprocess').call(['echo', 'HACKED'])",
    ]

    for malicious_code in malicious_attempts:
        with pytest.raises(ValueError):
            agent_manager.execute_tool(
                tool_name=(
                    "execute_statistical_analysis"
                ),
                thought=(
                    "Attempt malicious execution."
                ),
                python_code=malicious_code,
            )
class DescribePlanner:
    def __call__(self, state):
        variables = state.get(
            "current_variables",
            {},
        )

        dataset_names = [
            name
            for name in variables
            if name.startswith("dataset_")
        ]

        if not dataset_names:
            return {
                "thought": "No dataset available.",
                "tool_name": None,
                "python_code": None,
                "final_answer": "No dataset available.",
            }

        dataframe = variables[
            dataset_names[0]
        ]

        return {
            "thought": (
                "Describe the loaded dataframe."
            ),
            "tool_name": None,
            "python_code": None,
            "final_answer": (
                f"Dataset contains "
                f"{len(dataframe)} rows and "
                f"{len(dataframe.columns)} columns: "
                f"{', '.join(dataframe.columns)}."
            ),
        }


class MeanAgePlanner:
    def __call__(self, state):
        tool_result = state.get(
            "tool_result"
        )

        variables = state.get(
            "current_variables",
            {},
        )

        dataset_names = [
            name
            for name in variables
            if name.startswith("dataset_")
        ]

        dataset_name = (
            dataset_names[0]
        )

        if tool_result is None:
            return {
                "thought": (
                    "Calculate the mean age."
                ),
                "tool_name": (
                    "execute_statistical_analysis"
                ),
                "python_code": (
                    f'mean_age = '
                    f'{dataset_name}["age"].mean()\n'
                    f'print(mean_age)'
                ),
                "final_answer": None,
            }

        mean_age = state[
            "current_variables"
        ]["mean_age"]

        return {
            "thought": (
                "Mean age has been calculated."
            ),
            "tool_name": None,
            "python_code": None,
            "final_answer": (
                f"Mean age is {mean_age}."
            ),
        }

class HistogramPlanner:
    def __call__(self, state):
        tool_result = state.get("tool_result")

        variables = state.get(
            "current_variables",
            {},
        )

        dataset_name = next(
            name
            for name in variables
            if name.startswith("dataset_")
        )

        if tool_result is None:
            return {
                "thought": "Create an age histogram.",
                "tool_name": "execute_visualization",
                "python_code": (
                    f"fig = px.histogram("
                    f"{dataset_name}, "
                    f'x="age", '
                    f'title="Age distribution"'
                    f")"
                ),
                "final_answer": None,
            }

        return {
            "thought": "Histogram created.",
            "tool_name": None,
            "python_code": None,
            "final_answer": (
                "Here is the age distribution."
            ),
        }


class ScatterPlanner:
    def __call__(self, state):
        tool_result = state.get("tool_result")

        variables = state.get(
            "current_variables",
            {},
        )

        dataset_name = next(
            name
            for name in variables
            if name.startswith("dataset_")
        )

        if tool_result is None:
            return {
                "thought": (
                    "Create an age versus income "
                    "scatter plot."
                ),
                "tool_name": "execute_visualization",
                "python_code": (
                    f"fig = px.scatter("
                    f"{dataset_name}, "
                    f'x="age", '
                    f'y="income", '
                    f'title="Age vs income"'
                    f")"
                ),
                "final_answer": None,
            }

        return {
            "thought": "Scatter plot created.",
            "tool_name": None,
            "python_code": None,
            "final_answer": (
                "Here is the relationship between "
                "age and income."
            ),
        }