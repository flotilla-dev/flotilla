CREATE TABLE thread (
    thread_id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE thread_entry (
    entry_id VARCHAR PRIMARY KEY,
    thread_id VARCHAR NOT NULL,
    entry_order BIGINT NOT NULL,
    previous_entry_id VARCHAR NULL,
    created_at TIMESTAMP NOT NULL,
    type VARCHAR NOT NULL,
    actor_id VARCHAR NOT NULL,
    actor_type VARCHAR NOT NULL,
    phase_id VARCHAR NOT NULL,

    CONSTRAINT fk_thread_entry_thread
        FOREIGN KEY (thread_id)
        REFERENCES thread(thread_id),

    CONSTRAINT uq_thread_entry_order
        UNIQUE (thread_id, entry_order)
);

CREATE INDEX idx_thread_entry_thread_order
ON thread_entry (thread_id, entry_order ASC);

CREATE TABLE content_part (
    entry_id VARCHAR NOT NULL,
    part_index INT NOT NULL,
    part_type VARCHAR NOT NULL,
    serialized_payload TEXT NOT NULL,

    CONSTRAINT pk_content_part
        PRIMARY KEY (entry_id, part_index),

    CONSTRAINT fk_content_part_entry
        FOREIGN KEY (entry_id)
        REFERENCES thread_entry(entry_id)
);

CREATE INDEX idx_content_part_entry
ON content_part (entry_id);