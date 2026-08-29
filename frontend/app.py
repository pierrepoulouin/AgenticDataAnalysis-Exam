import os
import time

import plotly.graph_objects as go
import streamlit as st


# Compatibilité temporaire avec
# streamlit-cookies-manager.
if not hasattr(st, "cache"):
    st.cache = st.cache_data


from streamlit_cookies_manager import (
    EncryptedCookieManager,
)

from frontend.api_client import (
    APIError,
    create_session,
    get_agent_task_status,
    get_current_user,
    get_messages,
    list_datasets,
    list_message_visualizations,
    list_sessions,
    login,
    register,
    send_agent_message,
    upload_dataset,
)


st.set_page_config(
    page_title="Agentic Data Analysis",
    page_icon="📊",
    layout="wide",
)


cookie_password = os.getenv(
    "COOKIE_PASSWORD"
)

if not cookie_password:
    st.error(
        "COOKIE_PASSWORD n'est pas "
        "configuré."
    )
    st.stop()


cookies = EncryptedCookieManager(
    prefix="agentic_data_analysis/",
    password=cookie_password,
)


if not cookies.ready():
    st.stop()


def initialize_state() -> None:
    saved_token = cookies.get(
        "access_token"
    )

    defaults = {
        "access_token": saved_token,
        "current_user": None,
        "selected_session_id": None,
        "pending_task_id": None,
        "pending_task_session_id": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[
                key
            ] = value


def logout() -> None:
    st.session_state[
        "access_token"
    ] = None

    st.session_state[
        "current_user"
    ] = None

    st.session_state[
        "selected_session_id"
    ] = None

    st.session_state[
        "pending_task_id"
    ] = None

    st.session_state[
        "pending_task_session_id"
    ] = None

    if "access_token" in cookies:
        del cookies[
            "access_token"
        ]

        cookies.save()


def handle_auth_error(
    exc: APIError,
) -> None:
    if exc.status_code == 401:
        logout()

        st.warning(
            "Votre session a expiré. "
            "Veuillez vous reconnecter."
        )

        st.rerun()


def render_authentication() -> None:
    st.title(
        "📊 Agentic Data Analysis"
    )

    st.write(
        "Connectez-vous pour accéder "
        "à vos analyses."
    )

    login_tab, register_tab = st.tabs(
        [
            "Connexion",
            "Créer un compte",
        ]
    )

    with login_tab:
        with st.form(
            "login_form"
        ):
            email = st.text_input(
                "Email"
            )

            password = st.text_input(
                "Mot de passe",
                type="password",
            )

            submitted = (
                st.form_submit_button(
                    "Se connecter"
                )
            )

        if submitted:
            if (
                not email.strip()
                or not password
            ):
                st.warning(
                    "Veuillez renseigner "
                    "votre email et votre "
                    "mot de passe."
                )

            else:
                try:
                    auth = login(
                        email.strip(),
                        password,
                    )

                    token = auth[
                        "access_token"
                    ]

                    user = (
                        get_current_user(
                            token
                        )
                    )

                    st.session_state[
                        "access_token"
                    ] = token

                    st.session_state[
                        "current_user"
                    ] = user

                    cookies[
                        "access_token"
                    ] = token

                    cookies.save()

                    st.rerun()

                except APIError as exc:
                    if (
                        exc.status_code
                        == 401
                    ):
                        st.error(
                            "Email ou mot "
                            "de passe incorrect."
                        )

                    else:
                        st.error(
                            "Connexion "
                            f"impossible : {exc}"
                        )

    with register_tab:
        with st.form(
            "register_form"
        ):
            new_email = (
                st.text_input(
                    "Email",
                    key="register_email",
                )
            )

            new_password = (
                st.text_input(
                    "Mot de passe",
                    type="password",
                    key="register_password",
                )
            )

            submitted = (
                st.form_submit_button(
                    "Créer le compte"
                )
            )

        if submitted:
            if (
                not new_email.strip()
                or not new_password
            ):
                st.warning(
                    "Veuillez renseigner "
                    "un email et un mot "
                    "de passe."
                )

            else:
                try:
                    register(
                        new_email.strip(),
                        new_password,
                    )

                    st.success(
                        "Compte créé. "
                        "Vous pouvez vous "
                        "connecter."
                    )

                except APIError as exc:
                    if (
                        exc.status_code
                        == 409
                    ):
                        st.error(
                            "Ce compte "
                            "existe déjà."
                        )

                    else:
                        st.error(
                            "Création "
                            f"impossible : {exc}"
                        )


def load_authenticated_user(
    token: str,
) -> dict:
    try:
        user = get_current_user(
            token
        )

        st.session_state[
            "current_user"
        ] = user

        return user

    except APIError as exc:
        handle_auth_error(
            exc
        )

        st.error(
            "Backend indisponible : "
            f"{exc}"
        )

        st.stop()


def render_session_manager(
    token: str,
) -> None:
    st.subheader(
        "Sessions d'analyse"
    )

    try:
        sessions = list_sessions(
            token
        )

    except APIError as exc:
        handle_auth_error(
            exc
        )

        st.error(
            "Impossible de charger "
            f"les sessions : {exc}"
        )

        st.stop()

    with st.form(
        "create_session_form"
    ):
        title = st.text_input(
            "Nom de la nouvelle session",
            placeholder=(
                "Analyse des ventes 2026"
            ),
        )

        submitted = (
            st.form_submit_button(
                "Créer une session"
            )
        )

    if submitted:
        title = title.strip()

        if not title:
            st.warning(
                "Veuillez donner un nom "
                "à la session."
            )

        else:
            try:
                session = create_session(
                    token,
                    title,
                )

                st.session_state[
                    "selected_session_id"
                ] = session["id"]

                st.rerun()

            except APIError as exc:
                handle_auth_error(
                    exc
                )

                st.error(
                    "Création impossible : "
                    f"{exc}"
                )

    if not sessions:
        st.info(
            "Aucune session."
        )

        st.session_state[
            "selected_session_id"
        ] = None

        return

    options = {
        session["id"]: (
            session["title"]
        )
        for session in sessions
    }

    ids = list(
        options.keys()
    )

    current_id = st.session_state[
        "selected_session_id"
    ]

    if current_id not in ids:
        current_id = ids[0]

    selected_id = st.selectbox(
        "Session active",
        options=ids,
        index=ids.index(
            current_id
        ),
        format_func=lambda session_id: (
            f"#{session_id} — "
            f"{options[session_id]}"
        ),
    )

    st.session_state[
        "selected_session_id"
    ] = selected_id


def render_dataset_manager(
    token: str,
    session_id: int,
) -> None:
    st.subheader(
        "Données"
    )

    try:
        datasets = list_datasets(
            token
        )

    except APIError as exc:
        handle_auth_error(
            exc
        )

        st.error(
            "Impossible de charger "
            f"les datasets : {exc}"
        )

        return

    session_datasets = [
        dataset
        for dataset in datasets
        if (
            dataset.get(
                "session_id"
            )
            == session_id
        )
    ]

    if session_datasets:
        for dataset in (
            session_datasets
        ):
            st.caption(
                f"📄 {dataset['filename']}"
            )

    else:
        st.info(
            "Aucun dataset associé "
            "à cette session."
        )

    uploaded_file = (
        st.file_uploader(
            "Ajouter un CSV",
            type=["csv"],
            key=(
                f"upload_{session_id}"
            ),
        )
    )

    description = (
        st.text_input(
            "Description",
            key=(
                "dataset_description_"
                f"{session_id}"
            ),
        )
    )

    if st.button(
        "Uploader le dataset",
        key=(
            "upload_button_"
            f"{session_id}"
        ),
    ):
        if uploaded_file is None:
            st.warning(
                "Sélectionnez d'abord "
                "un fichier CSV."
            )

        else:
            try:
                dataset = upload_dataset(
                    token=token,
                    session_id=session_id,
                    uploaded_file=(
                        uploaded_file
                    ),
                    description=(
                        description.strip()
                    ),
                )

                st.success(
                    f"{dataset['filename']} "
                    "a été ajouté."
                )

                st.rerun()

            except APIError as exc:
                handle_auth_error(
                    exc
                )

                st.error(
                    "Upload impossible : "
                    f"{exc}"
                )


def render_chat(
    token: str,
    session_id: int,
) -> None:
    st.subheader(
        "Analyse"
    )

    try:
        messages = get_messages(
            token,
            session_id,
        )

    except APIError as exc:
        handle_auth_error(
            exc
        )

        st.error(
            "Impossible de charger "
            f"l'historique : {exc}"
        )

        return

    if not messages:
        st.info(
            "Aucun message. "
            "Posez une question."
        )

    for message in messages:
        role = message.get(
            "role"
        )

        if role not in {
            "user",
            "assistant",
        }:
            continue

        with st.chat_message(
            role
        ):
            st.markdown(
                message.get(
                    "content",
                    "",
                )
            )

            if role == "assistant":
                try:
                    visualizations = (
                        list_message_visualizations(
                            token=token,
                            message_id=(
                                message["id"]
                            ),
                        )
                    )

                except APIError as exc:
                    handle_auth_error(
                        exc
                    )

                    st.warning(
                        "Visualisations "
                        "indisponibles."
                    )

                    visualizations = []

                for visualization in (
                    visualizations
                ):
                    figure = go.Figure(
                        visualization[
                            "figure_json"
                        ]
                    )

                    st.plotly_chart(
                        figure,
                        use_container_width=True,
                        key=(
                            f"session_{session_id}"
                            f"_message_{message['id']}"
                            "_visualization_"
                            f"{visualization['id']}"
                        ),
                    )

    user_message = st.chat_input(
        "Posez une question "
        "sur vos données..."
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
            ] = task[
                "task_id"
            ]

            st.session_state[
                "pending_task_session_id"
            ] = session_id

            st.rerun()

        except APIError as exc:
            handle_auth_error(
                exc
            )

            st.error(
                "Impossible d'envoyer "
                f"le message : {exc}"
            )

    task_id = st.session_state[
        "pending_task_id"
    ]

    task_session_id = (
        st.session_state[
            "pending_task_session_id"
        ]
    )

    if (
        task_id is not None
        and task_session_id
        == session_id
    ):
        with st.status(
            "Analyse en cours...",
            expanded=True,
        ) as status_box:
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
                    handle_auth_error(
                        exc
                    )

                    status_box.update(
                        label=(
                            "Erreur pendant "
                            "l'analyse"
                        ),
                        state="error",
                    )

                    return

                current_status = (
                    result["status"]
                )

                if (
                    current_status
                    == "completed"
                ):
                    status_box.update(
                        label=(
                            "Analyse terminée"
                        ),
                        state="complete",
                    )

                    st.session_state[
                        "pending_task_id"
                    ] = None

                    st.session_state[
                        "pending_task_session_id"
                    ] = None

                    time.sleep(
                        0.3
                    )

                    st.rerun()

                if (
                    current_status
                    == "failed"
                ):
                    status_box.update(
                        label=(
                            "Analyse échouée"
                        ),
                        state="error",
                    )

                    st.session_state[
                        "pending_task_id"
                    ] = None

                    st.session_state[
                        "pending_task_session_id"
                    ] = None

                    return

                time.sleep(
                    0.5
                )

            status_box.update(
                label=(
                    "Analyse toujours "
                    "en cours"
                ),
                state="error",
            )


def render_authenticated_app() -> None:
    token = st.session_state[
        "access_token"
    ]

    if token is None:
        st.stop()

    user = load_authenticated_user(
        token
    )

    st.title(
        "📊 Agentic Data Analysis"
    )

    left, right = st.columns(
        [5, 1]
    )

    with left:
        st.success(
            "Connecté en tant que "
            f"{user['email']}"
        )

    with right:
        if st.button(
            "Se déconnecter",
            use_container_width=True,
        ):
            logout()
            st.rerun()

    st.divider()

    render_session_manager(
        token
    )

    session_id = st.session_state[
        "selected_session_id"
    ]

    if session_id is None:
        return

    st.divider()

    render_dataset_manager(
        token=token,
        session_id=session_id,
    )

    st.divider()

    # IMPORTANT :
    # UN SEUL appel à render_chat.
    render_chat(
        token=token,
        session_id=session_id,
    )


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