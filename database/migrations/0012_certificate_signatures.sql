-- Version 2 signatures bind recipient display name, description and achievement metadata.
ALTER TABLE certificates ADD COLUMN signature_version INTEGER NOT NULL DEFAULT 1 CHECK(signature_version IN (1,2));
