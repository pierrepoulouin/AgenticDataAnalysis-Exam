import os
import time
import plotly.graph_objects as go

import streamlit as st

# Compatibilité avec streamlit-cookies-manager,
# qui utilise encore l'ancien décorateur @st.cache.
if not hasattr(st, "cache"):
    st.cache = st.cache_data

from streamlit_cookies_manager import EncryptedCookieManager

from frontend.api_client import (
    APIError,
    create_session,
    get_agent_task_status,
    get_current_user,
    get_messages,
    list_message_visualizations,
    list_sessions,
    login,
    register,
    send_agent_message,
)


st.set_page_config(
    page_title="Agentic Data Analysis",
    page_icon="📊",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Cookies
# ---------------------------------------------------------------------------

cookie_password = os.getenv("COOKIE_PASSWORD")

if not cookie_password:
    st.error(
        "COOKIE_PASSWORD n'est pas configuré "
        "dans l'environnement."
    )
    st.stop()


cookies = EncryptedCookieManager(
    prefix="agentic_data_analysis/",
    password=cookie_password,
)


if not cookies.ready():
    st.stop()


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def initialize_state() -> None:
    """
    Initialise l'état local Streamlit.

    Si un JWT existe déjà dans le cookie chiffré,
    il est restauré après un refresh navigateur.
    """

    saved_token = cookies.get("access_token")

    defaults = {
        "access_token": saved_token,
        "current_user": None,
        "selected_session_id": None,
        "pending_task_id": None,
        "pending_task_session_id": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def logout() -> None:
    """
    Supprime l'état Streamlit et le JWT
    enregistré dans le cookie navigateur.
    """

    st.session_state["access_token"] = None
    st.session_state["current_user"] = None
    st.session_state["selected_session_id"] = None
    st.session_state["pending_task_id"] = None
    st.session_state["pending_task_session_id"] = None

    if "access_token" in cookies:
        del cookies["access_token"]
        cookies.save()


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def render_authentication() -> None:
    """Affiche les formulaires de connexion et d'inscription."""

    st.title("📊 Agentic Data Analysis")

    st.write(
        "Connectez-vous pour accéder à vos sessions "
        "d'analyse de données."
    )

    login_tab, register_tab = st.tabs(
        [
            "Connexion",
            "Créer un compte",
        ]
    )

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    with login_tab:
        with st.form("login_form"):
            email = st.text_input(
                "Email",
                key="login_email",
            )

            password = st.text_input(
                "Mot de passe",
                type="password",
                key="login_password",
            )

            submitted = st.form_submit_button(
                "Se connecter"
            )

        if submitted:
            if not email.strip() or not password:
                st.warning(
                    "Veuillez renseigner votre email "
                    "et votre mot de passe."
                )

            else:
                try:
                    auth = login(
                        email=email.strip(),
                        password=password,
                    )

                    token = auth["access_token"]

                    # FastAPI vérifie immédiatement
                    # que le JWT reçu est valide.
                    user = get_current_user(token)

                    st.session_state[
                        "access_token"
                    ] = token

                    st.session_state[
                        "current_user"
                    ] = user

                    # Persistance navigateur.
                    cookies["access_token"] = token
                    cookies.save()

                    st.rerun()

                except APIError as exc:
                    if exc.status_code == 401:
                        st.error(
                            "Email ou mot de passe incorrect."
                        )

                    else:
                        st.error(
                            f"Connexion impossible : {exc}"
                        )

    # ------------------------------------------------------------------
    # Register
    # ------------------------------------------------------------------

    with register_tab:
        with st.form("register_form"):
            new_email = st.text_input(
                "Email",
                key="register_email",
            )

            new_password = st.text_input(
                "Mot de passe",
                type="password",
                key="register_password",
            )

            register_submitted = st.form_submit_button(
                "Créer le compte"
            )

        if register_submitted:
            if (
                not new_email.strip()
                or not new_password
            ):
                st.warning(
                    "Veuillez renseigner un email "
                    "et un mot de passe."
                )

            else:
                try:
                    register(
                        email=new_email.strip(),
                        password=new_password,
                    )

                    st.success(
                        "Compte créé avec succès. "
                        "Vous pouvez maintenant "
                        "vous connecter."
                    )

                except APIError as exc:
                    if exc.status_code == 409:
                        st.error(
                            "Un compte existe déjà "
                            "avec cet email."
                        )

                    else:
                        st.error(
                            f"Création impossible : {exc}"
                        )


def load_authenticated_user(
    token: str,
) -> dict:
    """
    Vérifie le JWT auprès de FastAPI
    et récupère l'utilisateur courant.
    """

    try:
        user = get_current_user(token)

        st.session_state[
            "current_user"
        ] = user

        return user

    except APIError as exc:
        if exc.status_code == 401:
            # JWT expiré ou invalide :
            # on nettoie aussi le cookie.
            logout()

            st.warning(
                "Votre session a expiré. "
                "Veuillez vous reconnecter."
            )

            st.rerun()

        st.error(
            f"Impossible de contacter "
            f"le backend : {exc}"
        )

        st.stop()


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def render_session_manager(
    token: str,
) -> None:
    """Affiche et crée les sessions d'analyse."""

    st.subheader("Sessions d'analyse")

    try:
        sessions = list_sessions(token)

    except APIError as exc:
        if exc.status_code == 401:
            logout()
            st.rerun()

        st.error(
            f"Impossible de charger "
            f"les sessions : {exc}"
        )

        st.stop()

    # ------------------------------------------------------------------
    # Create session
    # ------------------------------------------------------------------

    with st.form("create_session_form"):
        session_title = st.text_input(
            "Nom de la nouvelle session",
            placeholder="Analyse des ventes 2026",
        )

        create_submitted = (
            st.form_submit_button(
                "Créer une session"
            )
        )

    if create_submitted:
        clean_title = session_title.strip()

        if not clean_title:
            st.warning(
                "Veuillez donner un nom "
                "à la session."
            )

        else:
            try:
                new_session = create_session(
                    token=token,
                    title=clean_title,
                )

                st.session_state[
                    "selected_session_id"
                ] = new_session["id"]

                st.success(
                    "Session créée avec succès."
                )

                st.rerun()

            except APIError as exc:
                if exc.status_code == 401:
                    logout()
                    st.rerun()

                st.error(
                    f"Création impossible : {exc}"
                )

    # ------------------------------------------------------------------
    # Session selector
    # ------------------------------------------------------------------

    if not sessions:
        st.info(
            "Aucune session d'analyse "
            "pour le moment. "
            "Créez votre première session."
        )

        st.session_state[
            "selected_session_id"
        ] = None

        return

    session_options = {
        session["id"]: session["title"]
        for session in sessions
    }

    session_ids = list(
        session_options.keys()
    )

    current_session_id = st.session_state[
        "selected_session_id"
    ]

    if current_session_id not in session_ids:
        current_session_id = session_ids[0]

        st.session_state[
            "selected_session_id"
        ] = current_session_id

    selected_index = session_ids.index(
        current_session_id
    )

    selected_session_id = st.selectbox(
        "Session active",
        options=session_ids,
        index=selected_index,
        format_func=lambda session_id: (
            f"#{session_id} — "
            f"{session_options[session_id]}"
        ),
    )

    st.session_state[
        "selected_session_id"
    ] = selected_session_id

    st.caption(
        f"Session ID : {selected_session_id}"
    )


# ---------------------------------------------------------------------------
# Agent chat
# ---------------------------------------------------------------------------

def render_chat(
    token: str,
    session_id: int,
) -> None:
    """
    Affiche l'historique persistant
    et permet d'interroger l'agent.
    """

    st.subheader("Analyse")

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    try:
        messages = get_messages(
            token=token,
            session_id=session_id,
        )

    except APIError as exc:
        if exc.status_code == 401:
            logout()
            st.rerun()

        st.error(
            f"Impossible de charger "
            f"l'historique : {exc}"
        )

        return

    if not messages:
        st.info(
            "Aucun message dans cette session. "
            "Posez votre première question "
            "à l'agent."
        )

    for message in messages:
        role = message.get("role")

        if role not in {
            "user",
            "assistant",
        }:
            continue

        with st.chat_message(role):
            st.markdown(
                message.get("content", "")
            )

            try:
                visualizations = (
                    list_message_visualizations(
                        token=token,
                        message_id=message["id"],
                    )
                )

            except APIError as exc:
                st.warning(
                    "Impossible de charger "
                    f"les visualisations : {exc}"
                )
                visualizations = []

            for visualization in visualizations:
                figure = go.Figure(
                    visualization["figure_json"]
                )

                st.plotly_chart(
                    figure,
                    use_container_width=True,
                )

    # ------------------------------------------------------------------
    # New message
    # ------------------------------------------------------------------

    user_message = st.chat_input(
        "Posez une question sur vos données..."
    )

    if user_message:
        try:
            task = send_agent_message(
                token=token,
                session_id=session_id,
                message=user_message,
            )

            st.session_state[
                "pending_task_id"
            ] = task["task_id"]

            st.session_state[
                "pending_task_session_id"
            ] = session_id

            st.rerun()

        except APIError as exc:
            if exc.status_code == 401:
                logout()
                st.rerun()

            st.error(
                f"Impossible d'envoyer "
                f"le message : {exc}"
            )

    # ------------------------------------------------------------------
    # Celery task polling
    # ------------------------------------------------------------------

    task_id = st.session_state[
        "pending_task_id"
    ]

    task_session_id = st.session_state[
        "pending_task_session_id"
    ]

    if (
        task_id is not None
        and task_session_id == session_id
    ):
        with st.status(
            "Analyse en cours...",
            expanded=True,
        ) as task_status:

            for _ in range(60):
                try:
                    result = (
                        get_agent_task_status(
                            token=token,
                            session_id=session_id,
                            task_id=task_id,
                        )
                    )

                except APIError as exc:
                    if exc.status_code == 401:
                        logout()
                        st.rerun()

                    task_status.update(
                        label=(
                            "Erreur pendant "
                            "l'analyse"
                        ),
                        state="error",
                    )

                    st.error(str(exc))
                    return

                current_status = result[
                    "status"
                ]

                st.write(
                    f"État : {current_status}"
                )

                if current_status == "completed":
                    task_status.update(
                        label="Analyse terminée",
                        state="complete",
                    )

                    st.session_state[
                        "pending_task_id"
                    ] = None

                    st.session_state[
                        "pending_task_session_id"
                    ] = None

                    time.sleep(0.5)
                    st.rerun()

                if current_status == "failed":
                    task_status.update(
                        label="L'analyse a échoué",
                        state="error",
                    )

                    st.session_state[
                        "pending_task_id"
                    ] = None

                    st.session_state[
                        "pending_task_session_id"
                    ] = None

                    return

                time.sleep(0.5)

            task_status.update(
                label=(
                    "L'analyse prend plus "
                    "de temps que prévu"
                ),
                state="error",
            )

            st.warning(
                "La tâche continue peut-être "
                "en arrière-plan. "
                "Rechargez la page pour "
                "consulter l'historique."
            )


# ---------------------------------------------------------------------------
# Authenticated application
# ---------------------------------------------------------------------------

def render_authenticated_app() -> None:
    """Affiche l'application utilisateur."""

    token = st.session_state[
        "access_token"
    ]

    if token is None:
        st.stop()

    # Le cookie ne suffit jamais à autoriser
    # l'utilisateur : FastAPI vérifie le JWT.
    user = load_authenticated_user(token)

    if user is None:
        st.error(
            "Impossible de récupérer "
            "l'utilisateur connecté."
        )
        st.stop()

    st.title(
        "📊 Agentic Data Analysis"
    )

    header_col, logout_col = st.columns(
        [5, 1]
    )

    with header_col:
        st.success(
            f"Connecté en tant que "
            f"{user['email']}"
        )

    with logout_col:
        if st.button(
            "Se déconnecter",
            use_container_width=True,
        ):
            logout()
            st.rerun()

    st.divider()

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    render_session_manager(token)

    selected_session_id = st.session_state[
        "selected_session_id"
    ]

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    if selected_session_id is not None:
        st.divider()

        render_chat(
            token=token,
            session_id=selected_session_id,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    initialize_state()

    if (
        st.session_state[
            "access_token"
        ]
        is None
    ):
        render_authentication()
        return

    render_authenticated_app()


if __name__ == "__main__":
    main()