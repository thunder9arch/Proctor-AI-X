CREATE DATABASE IF NOT EXISTS devvault
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE devvault;

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS snippets (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(180) NOT NULL,
    code MEDIUMTEXT NOT NULL,
    language VARCHAR(80) NOT NULL,
    tags VARCHAR(255) NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_viewed_at TIMESTAMP NULL DEFAULT NULL,
    last_copied_at TIMESTAMP NULL DEFAULT NULL,
    search_text MEDIUMTEXT GENERATED ALWAYS AS (CONCAT_WS(' ', title, tags, code)) STORED,
    INDEX idx_snippets_language (language),
    INDEX idx_snippets_created_at (created_at),
    INDEX idx_snippets_updated_at (updated_at),
    INDEX idx_snippets_last_copied_at (last_copied_at),
    FULLTEXT INDEX ft_snippets_search (title, tags, code)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS snippet_usage (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    snippet_id INT UNSIGNED NOT NULL,
    action_type ENUM('view', 'copy', 'edit', 'create', 'favorite') NOT NULL,
    used_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usage_snippet_action (snippet_id, action_type),
    INDEX idx_usage_used_at (used_at),
    CONSTRAINT fk_usage_snippet
        FOREIGN KEY (snippet_id) REFERENCES snippets(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS favorites (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    snippet_id INT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_favorites_snippet (snippet_id),
    INDEX idx_favorites_created_at (created_at),
    CONSTRAINT fk_favorites_snippet
        FOREIGN KEY (snippet_id) REFERENCES snippets(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS collections (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    description VARCHAR(255) NOT NULL DEFAULT '',
    color VARCHAR(20) NOT NULL DEFAULT '#4f46e5',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_collections_name (name)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS collection_snippets (
    collection_id INT UNSIGNED NOT NULL,
    snippet_id INT UNSIGNED NOT NULL,
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (collection_id, snippet_id),
    INDEX idx_collection_snippets_snippet (snippet_id),
    CONSTRAINT fk_collection_snippets_collection
        FOREIGN KEY (collection_id) REFERENCES collections(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_collection_snippets_snippet
        FOREIGN KEY (snippet_id) REFERENCES snippets(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS snippet_versions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    snippet_id INT UNSIGNED NOT NULL,
    title VARCHAR(180) NOT NULL,
    code MEDIUMTEXT NOT NULL,
    language VARCHAR(80) NOT NULL,
    tags VARCHAR(255) NOT NULL DEFAULT '',
    version_note VARCHAR(190) NOT NULL DEFAULT 'Previous revision',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_versions_snippet_created_at (snippet_id, created_at),
    CONSTRAINT fk_versions_snippet
        FOREIGN KEY (snippet_id) REFERENCES snippets(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

INSERT INTO collections (name, description, color)
VALUES
    ('Frontend', 'UI patterns, layout snippets, and browser helpers', '#2563eb'),
    ('Backend', 'API utilities, validation helpers, and DB snippets', '#059669'),
    ('Tooling', 'CLI scripts, build steps, and automation helpers', '#dc2626')
ON DUPLICATE KEY UPDATE
    description = VALUES(description),
    color = VALUES(color);
