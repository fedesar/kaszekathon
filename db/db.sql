CREATE TABLE claude_code_otel_ingest (
    id                         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    created_at                 TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    id_organization            INT UNSIGNED    NOT NULL,
    signal_type                VARCHAR(16)     NOT NULL,
    http_method                VARCHAR(8)      NOT NULL,
    request_path               VARCHAR(255)    NOT NULL,
    request_id                 VARCHAR(128)    NULL,
    content_type               VARCHAR(255)    NULL,
    source_ip                  VARCHAR(64)     NULL,
    user_agent                 VARCHAR(512)    NULL,
    authorization_scheme       VARCHAR(32)     NULL,
    authorization_token_sha256 CHAR(64)        NOT NULL,
    authorization_token_hint   VARCHAR(32)     NOT NULL,
    body_sha256                CHAR(64)        NOT NULL,
    body_size_bytes            INT UNSIGNED    NOT NULL,
    payload_encoding           VARCHAR(16)     NOT NULL,
    payload_text               LONGTEXT        NOT NULL,
    headers_json               LONGTEXT        NOT NULL,
    query_json                 LONGTEXT        NOT NULL,

    PRIMARY KEY (id),
    INDEX idx_id_organization (id_organization),
    INDEX idx_signal_type (signal_type),
    INDEX idx_request_id (request_id),
    INDEX idx_authorization_token_sha256 (authorization_token_sha256)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE repositories (
    id_repository            INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    repository_app_id        VARCHAR(255)    NOT NULL,
    repository_name          VARCHAR(255)    NOT NULL,
    owner                    VARCHAR(255)    NULL,
    description              VARCHAR(1024)   NULL,
    path                     VARCHAR(512)    NULL,
    default_branch           VARCHAR(255)    NULL,
    last_updated             DATETIME        NULL,
    active                   TINYINT(1)      NOT NULL DEFAULT 1,
    repository_creation_date DATETIME        NULL,
    created_at               DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id_repository),
    INDEX idx_repository_app_id (repository_app_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE repo_merge_requests (
    id_merge_request       INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    id_repository          INT UNSIGNED    NOT NULL,
    merge_request_app_id   VARCHAR(255)    NOT NULL,
    title                  VARCHAR(512)    NULL,
    description            TEXT            NULL,
    url                    VARCHAR(1024)   NULL,
    state                  VARCHAR(32)     NOT NULL,
    creation_date          DATETIME        NULL,
    merged_at              DATETIME        NULL,
    first_approval_at      DATETIME        NULL,
    first_approval_by      VARCHAR(255)    NULL,
    closed_at              DATETIME        NULL,
    source_branch          VARCHAR(255)    NULL,
    target_branch          VARCHAR(255)    NULL,
    comments_count         INT UNSIGNED    NOT NULL DEFAULT 0,
    lines_added            INT UNSIGNED    NOT NULL DEFAULT 0,
    lines_deleted          INT UNSIGNED    NOT NULL DEFAULT 0,
    author_internal_id     INT UNSIGNED    NULL,
    author_app_id          VARCHAR(255)    NULL,
    author_name            VARCHAR(255)    NULL,
    created_at             DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at             DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id_merge_request),
    INDEX idx_id_repository (id_repository),
    INDEX idx_merge_request_app_id (merge_request_app_id),
    INDEX idx_state (state),

    CONSTRAINT fk_mr_repository
        FOREIGN KEY (id_repository) REFERENCES repositories (id_repository)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE repo_commits (
    id_commit              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    id_repository          INT UNSIGNED    NOT NULL,
    merge_request_id       INT UNSIGNED    NULL,
    commit_app_id          VARCHAR(255)    NOT NULL,
    title                  VARCHAR(512)    NULL,
    message                TEXT            NULL,
    author_internal_id     INT UNSIGNED    NULL,
    author_app_id          VARCHAR(255)    NULL,
    author_name            VARCHAR(255)    NULL,
    author_email           VARCHAR(255)    NULL,
    commit_creation_date   DATETIME        NULL,
    lines_added            INT UNSIGNED    NOT NULL DEFAULT 0,
    lines_deleted          INT UNSIGNED    NOT NULL DEFAULT 0,
    created_at             DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at             DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id_commit),
    INDEX idx_id_repository (id_repository),
    INDEX idx_merge_request_id (merge_request_id),
    INDEX idx_commit_app_id (commit_app_id),

    CONSTRAINT fk_commit_repository
        FOREIGN KEY (id_repository) REFERENCES repositories (id_repository),
    CONSTRAINT fk_commit_merge_request
        FOREIGN KEY (merge_request_id) REFERENCES repo_merge_requests (id_merge_request)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE user_identity_map (
    id_user              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    display_name         VARCHAR(255)    NOT NULL,
    git_email            VARCHAR(255)    NOT NULL,
    auth_token_sha256    CHAR(64)        NOT NULL,

    created_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id_user),
    UNIQUE INDEX uq_auth_token (auth_token_sha256),
    UNIQUE INDEX uq_git_email (git_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;