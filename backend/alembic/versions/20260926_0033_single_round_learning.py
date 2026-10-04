"""Create single-round learning persistence and detach bank sources."""

from __future__ import annotations

from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision = "20260926_0033"
down_revision = "20260924_0032"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    if table not in _tables():
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


ROUTE_TABLE_NAMES = (
    "learning_routes",
    "learning_route_steps",
    "route_reading_progress",
    "route_case_sessions",
    "route_case_messages",
    "route_case_phase_decisions",
    "route_final_tests",
    "route_test_questions",
    "route_test_attempts",
    "route_learning_results",
    "route_test_review_events",
    "route_command_receipts",
)

FROZEN_ROUTE_SCHEMA = {
    "postgresql": {
        "learning_route_steps": {
            "columns": (
                "id",
                "public_id",
                "route_id",
                "position",
                "kind",
                "title",
                "goal_point_codes",
                "source_snapshot",
                "public_definition",
                "private_definition",
                "status",
                "completed_at",
                "created_at",
                "updated_at",
            ),
            "indexes": (
                "CREATE INDEX ix_learning_route_steps_route_status ON learning_route_steps (route_id, status)",
            ),
            "table": "\n"
            "CREATE TABLE learning_route_steps (\n"
            "\tid SERIAL NOT NULL, \n"
            "\tpublic_id VARCHAR(36) NOT NULL, \n"
            "\troute_id INTEGER NOT NULL, \n"
            "\tposition INTEGER NOT NULL, \n"
            "\tkind VARCHAR(12) NOT NULL, \n"
            "\ttitle VARCHAR(200) DEFAULT '' NOT NULL, \n"
            "\tgoal_point_codes JSON DEFAULT '[]' NOT NULL, \n"
            "\tsource_snapshot JSON DEFAULT '{}' NOT NULL, \n"
            "\tpublic_definition JSON DEFAULT '{}' NOT NULL, \n"
            "\tprivate_definition JSON DEFAULT '{}' NOT NULL, \n"
            "\tstatus VARCHAR(16) DEFAULT 'locked' NOT NULL, \n"
            "\tcompleted_at TIMESTAMP WITH TIME ZONE, \n"
            "\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_learning_route_step_public_id UNIQUE "
            "(public_id), \n"
            "\tCONSTRAINT uq_learning_route_step_position UNIQUE (route_id, "
            "position), \n"
            "\tCONSTRAINT ck_learning_route_step_position CHECK (position >= "
            "1), \n"
            "\tCONSTRAINT ck_learning_route_step_kind CHECK (kind IN "
            "('reading', 'case')), \n"
            "\tCONSTRAINT ck_learning_route_step_status CHECK (status IN "
            "('locked', 'available', 'in_progress', 'completed', "
            "'blocked')), \n"
            "\tFOREIGN KEY(route_id) REFERENCES learning_routes (id) ON DELETE "
            "RESTRICT\n"
            ")\n"
            "\n",
        },
        "learning_routes": {
            "columns": (
                "id",
                "public_id",
                "student_id",
                "source_participation_id",
                "session_id",
                "completion_snapshot_id",
                "source_kind",
                "class_id",
                "teacher_id",
                "title",
                "goal_point_codes",
                "diagnosis_summary",
                "generation_context",
                "generation_state",
                "generation_claim_token",
                "generation_claim_expires_at",
                "generation_execution_state",
                "error_code",
                "content_version",
                "content_digest",
                "published_at",
                "route_completed_at",
                "created_at",
                "updated_at",
            ),
            "indexes": (
                "CREATE INDEX ix_learning_route_class_created ON learning_routes (class_id, created_at)",
                "CREATE INDEX ix_learning_route_student_created ON learning_routes (student_id, created_at)",
            ),
            "table": "\n"
            "CREATE TABLE learning_routes (\n"
            "\tid SERIAL NOT NULL, \n"
            "\tpublic_id VARCHAR(36) NOT NULL, \n"
            "\tstudent_id INTEGER NOT NULL, \n"
            "\tsource_participation_id INTEGER NOT NULL, \n"
            "\tsession_id INTEGER NOT NULL, \n"
            "\tcompletion_snapshot_id INTEGER NOT NULL, \n"
            "\tsource_kind VARCHAR(20) NOT NULL, \n"
            "\tclass_id INTEGER, \n"
            "\tteacher_id INTEGER, \n"
            "\ttitle VARCHAR(200) DEFAULT '学习计划' NOT NULL, \n"
            "\tgoal_point_codes JSON DEFAULT '[]' NOT NULL, \n"
            "\tdiagnosis_summary JSON DEFAULT '{}' NOT NULL, \n"
            "\tgeneration_context JSON DEFAULT '{}' NOT NULL, \n"
            "\tgeneration_state VARCHAR(24) DEFAULT 'pending' NOT NULL, \n"
            "\tgeneration_claim_token VARCHAR(100), \n"
            "\tgeneration_claim_expires_at TIMESTAMP WITH TIME ZONE, \n"
            "\tgeneration_execution_state VARCHAR(12), \n"
            "\terror_code VARCHAR(80), \n"
            "\tcontent_version INTEGER, \n"
            "\tcontent_digest VARCHAR(64), \n"
            "\tpublished_at TIMESTAMP WITH TIME ZONE, \n"
            "\troute_completed_at TIMESTAMP WITH TIME ZONE, \n"
            "\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_learning_route_participation UNIQUE "
            "(source_participation_id), \n"
            "\tCONSTRAINT uq_learning_route_public_id UNIQUE (public_id), \n"
            "\tCONSTRAINT ck_learning_route_source_kind CHECK (source_kind IN "
            "('classroom', 'autonomous')), \n"
            "\tCONSTRAINT ck_learning_route_generation_state CHECK "
            "(generation_state IN ('pending', 'generating', 'published', "
            "'generation_failed')), \n"
            "\tCONSTRAINT ck_learning_route_source_scope CHECK ((source_kind = "
            "'classroom' AND class_id IS NOT NULL AND teacher_id IS NOT NULL) OR "
            "(source_kind = 'autonomous' AND class_id IS NULL AND teacher_id IS "
            "NULL)), \n"
            "\tCONSTRAINT ck_learning_route_content_version CHECK (content_version "
            "IS NULL OR content_version >= 1), \n"
            "\tFOREIGN KEY(student_id) REFERENCES users (id) ON DELETE RESTRICT, \n"
            "\tFOREIGN KEY(source_participation_id) REFERENCES pbl_participations "
            "(id) ON DELETE RESTRICT, \n"
            "\tFOREIGN KEY(session_id) REFERENCES pbl_sessions (id) ON DELETE "
            "RESTRICT, \n"
            "\tFOREIGN KEY(completion_snapshot_id) REFERENCES "
            "pbl_diagnostic_snapshots (id) ON DELETE RESTRICT, \n"
            "\tFOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE RESTRICT, \n"
            "\tFOREIGN KEY(teacher_id) REFERENCES users (id) ON DELETE RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_case_messages": {
            "columns": (
                "id",
                "case_session_id",
                "sequence",
                "role",
                "content",
                "client_message_id",
                "request_revision",
                "processing_status",
                "processing_token",
                "processing_expires_at",
                "payload_digest",
                "error_code",
                "created_at",
                "updated_at",
            ),
            "indexes": (
                "CREATE INDEX ix_route_case_message_session_revision ON "
                "route_case_messages (case_session_id, request_revision)",
            ),
            "table": "\n"
            "CREATE TABLE route_case_messages (\n"
            "\tid SERIAL NOT NULL, \n"
            "\tcase_session_id INTEGER NOT NULL, \n"
            "\tsequence INTEGER NOT NULL, \n"
            "\trole VARCHAR(12) NOT NULL, \n"
            "\tcontent TEXT NOT NULL, \n"
            "\tclient_message_id VARCHAR(100), \n"
            "\trequest_revision INTEGER NOT NULL, \n"
            "\tprocessing_status VARCHAR(16) DEFAULT 'completed' NOT NULL, \n"
            "\tprocessing_token VARCHAR(100), \n"
            "\tprocessing_expires_at TIMESTAMP WITH TIME ZONE, \n"
            "\tpayload_digest VARCHAR(64), \n"
            "\terror_code VARCHAR(80), \n"
            "\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_case_message_sequence UNIQUE "
            "(case_session_id, sequence), \n"
            "\tCONSTRAINT uq_route_case_message_client_id UNIQUE "
            "(case_session_id, client_message_id), \n"
            "\tCONSTRAINT ck_route_case_message_sequence CHECK (sequence >= "
            "1), \n"
            "\tCONSTRAINT ck_route_case_message_role CHECK (role IN ('student', "
            "'assistant')), \n"
            "\tCONSTRAINT ck_route_case_message_processing_status CHECK "
            "(processing_status IN ('pending', 'processing', 'completed', "
            "'failed', 'blocked')), \n"
            "\tCONSTRAINT ck_route_case_message_revision CHECK "
            "(request_revision >= 1), \n"
            "\tFOREIGN KEY(case_session_id) REFERENCES route_case_sessions (id) "
            "ON DELETE RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_case_phase_decisions": {
            "columns": (
                "id",
                "case_session_id",
                "message_id",
                "revision",
                "phase",
                "decision",
                "evidence_message_ids",
                "satisfied_goal_codes",
                "missing_goal_codes",
                "safety_status",
                "created_at",
            ),
            "indexes": (),
            "table": "\n"
            "CREATE TABLE route_case_phase_decisions (\n"
            "\tid SERIAL NOT NULL, \n"
            "\tcase_session_id INTEGER NOT NULL, \n"
            "\tmessage_id INTEGER NOT NULL, \n"
            "\trevision INTEGER NOT NULL, \n"
            "\tphase VARCHAR(32) NOT NULL, \n"
            "\tdecision VARCHAR(12) NOT NULL, \n"
            "\tevidence_message_ids JSON DEFAULT '[]' NOT NULL, \n"
            "\tsatisfied_goal_codes JSON DEFAULT '[]' NOT NULL, \n"
            "\tmissing_goal_codes JSON DEFAULT '[]' NOT NULL, \n"
            "\tsafety_status VARCHAR(12) NOT NULL, \n"
            "\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT "
            "NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_case_decision_revision UNIQUE "
            "(case_session_id, revision), \n"
            "\tCONSTRAINT uq_route_case_decision_message UNIQUE "
            "(message_id), \n"
            "\tCONSTRAINT ck_route_case_decision_phase CHECK (phase IN "
            "('pathology_recognition', 'mechanism_explanation', "
            "'evidence_judgment')), \n"
            "\tCONSTRAINT ck_route_case_decision_value CHECK (decision "
            "IN ('stay', 'advance', 'complete')), \n"
            "\tCONSTRAINT ck_route_case_decision_safety CHECK "
            "(safety_status IN ('educational', 'unsafe')), \n"
            "\tFOREIGN KEY(case_session_id) REFERENCES "
            "route_case_sessions (id) ON DELETE RESTRICT, \n"
            "\tFOREIGN KEY(message_id) REFERENCES route_case_messages "
            "(id) ON DELETE RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_case_sessions": {
            "columns": (
                "id",
                "public_id",
                "step_id",
                "student_id",
                "phase",
                "revision",
                "phase_started_revision",
                "status",
                "completed_at",
                "created_at",
                "updated_at",
            ),
            "indexes": (),
            "table": "\n"
            "CREATE TABLE route_case_sessions (\n"
            "\tid SERIAL NOT NULL, \n"
            "\tpublic_id VARCHAR(36) NOT NULL, \n"
            "\tstep_id INTEGER NOT NULL, \n"
            "\tstudent_id INTEGER NOT NULL, \n"
            "\tphase VARCHAR(32) DEFAULT 'pathology_recognition' NOT NULL, \n"
            "\trevision INTEGER DEFAULT '0' NOT NULL, \n"
            "\tphase_started_revision INTEGER DEFAULT '0' NOT NULL, \n"
            "\tstatus VARCHAR(16) DEFAULT 'in_progress' NOT NULL, \n"
            "\tcompleted_at TIMESTAMP WITH TIME ZONE, \n"
            "\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_case_session_public_id UNIQUE (public_id), \n"
            "\tCONSTRAINT uq_route_case_session_step UNIQUE (step_id), \n"
            "\tCONSTRAINT ck_route_case_session_phase CHECK (phase IN "
            "('pathology_recognition', 'mechanism_explanation', "
            "'evidence_judgment', 'completed')), \n"
            "\tCONSTRAINT ck_route_case_session_revision CHECK (revision >= "
            "0), \n"
            "\tCONSTRAINT ck_route_case_session_phase_revision CHECK "
            "(phase_started_revision >= 0), \n"
            "\tCONSTRAINT ck_route_case_session_status CHECK (status IN "
            "('in_progress', 'blocked', 'completed')), \n"
            "\tFOREIGN KEY(step_id) REFERENCES learning_route_steps (id) ON "
            "DELETE RESTRICT, \n"
            "\tFOREIGN KEY(student_id) REFERENCES users (id) ON DELETE "
            "RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_command_receipts": {
            "columns": (
                "id",
                "actor_id",
                "operation",
                "client_request_id",
                "payload_digest",
                "resource_kind",
                "resource_public_id",
                "result_version",
                "response_locator",
                "response_snapshot",
                "created_at",
            ),
            "indexes": (
                "CREATE INDEX ix_route_command_receipt_resource ON route_command_receipts (resource_public_id)",
            ),
            "table": "\n"
            "CREATE TABLE route_command_receipts (\n"
            "\tid SERIAL NOT NULL, \n"
            "\tactor_id INTEGER NOT NULL, \n"
            "\toperation VARCHAR(60) NOT NULL, \n"
            "\tclient_request_id VARCHAR(100) NOT NULL, \n"
            "\tpayload_digest VARCHAR(64) NOT NULL, \n"
            "\tresource_kind VARCHAR(40) NOT NULL, \n"
            "\tresource_public_id VARCHAR(36) NOT NULL, \n"
            "\tresult_version INTEGER NOT NULL, \n"
            "\tresponse_locator VARCHAR(200), \n"
            "\tresponse_snapshot JSON, \n"
            "\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_command_request UNIQUE (actor_id, "
            "operation, client_request_id), \n"
            "\tCONSTRAINT ck_route_command_receipt_result_version CHECK "
            "(result_version >= 1), \n"
            "\tFOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE "
            "RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_final_tests": {
            "columns": (
                "id",
                "public_id",
                "title",
                "route_id",
                "generation_state",
                "generation_claim_token",
                "generation_claim_expires_at",
                "generation_execution_state",
                "error_code",
                "review_state",
                "review_kind",
                "feedback_draft",
                "version",
                "draft_digest",
                "released_version",
                "released_digest",
                "released_at",
                "reviewer_id",
                "created_at",
                "updated_at",
            ),
            "indexes": ("CREATE INDEX ix_route_final_test_generation_state ON route_final_tests (generation_state)",),
            "table": "\n"
            "CREATE TABLE route_final_tests (\n"
            "\tid SERIAL NOT NULL, \n"
            "\tpublic_id VARCHAR(36) NOT NULL, \n"
            "\ttitle VARCHAR(200) DEFAULT '最终测试' NOT NULL, \n"
            "\troute_id INTEGER NOT NULL, \n"
            "\tgeneration_state VARCHAR(24) DEFAULT 'pending' NOT NULL, \n"
            "\tgeneration_claim_token VARCHAR(100), \n"
            "\tgeneration_claim_expires_at TIMESTAMP WITH TIME ZONE, \n"
            "\tgeneration_execution_state VARCHAR(12), \n"
            "\terror_code VARCHAR(80), \n"
            "\treview_state VARCHAR(20) DEFAULT 'pending_review' NOT NULL, \n"
            "\treview_kind VARCHAR(12) DEFAULT 'teacher' NOT NULL, \n"
            "\tfeedback_draft TEXT DEFAULT '' NOT NULL, \n"
            "\tversion INTEGER DEFAULT '1' NOT NULL, \n"
            "\tdraft_digest VARCHAR(64), \n"
            "\treleased_version INTEGER, \n"
            "\treleased_digest VARCHAR(64), \n"
            "\treleased_at TIMESTAMP WITH TIME ZONE, \n"
            "\treviewer_id INTEGER, \n"
            "\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_final_test_public_id UNIQUE (public_id), \n"
            "\tCONSTRAINT uq_route_final_test_route UNIQUE (route_id), \n"
            "\tCONSTRAINT ck_route_final_test_generation_state CHECK "
            "(generation_state IN ('pending', 'generating', 'ready', "
            "'generation_failed')), \n"
            "\tCONSTRAINT ck_route_final_test_review_state CHECK (review_state IN "
            "('pending_review', 'needs_changes', 'released')), \n"
            "\tCONSTRAINT ck_route_final_test_review_kind CHECK (review_kind IN "
            "('teacher', 'ai_direct')), \n"
            "\tCONSTRAINT ck_route_final_test_version CHECK (version >= 1), \n"
            "\tCONSTRAINT ck_route_final_test_released_version CHECK "
            "(released_version IS NULL OR released_version >= 1), \n"
            "\tCONSTRAINT ck_route_final_test_reviewer_scope CHECK ((review_kind "
            "= 'ai_direct' AND reviewer_id IS NULL AND review_state = 'released') "
            "OR (review_kind = 'teacher' AND (review_state != 'released' OR "
            "reviewer_id IS NOT NULL))), \n"
            "\tFOREIGN KEY(route_id) REFERENCES learning_routes (id) ON DELETE "
            "RESTRICT, \n"
            "\tFOREIGN KEY(reviewer_id) REFERENCES users (id) ON DELETE RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_learning_results": {
            "columns": (
                "id",
                "public_id",
                "route_id",
                "attempt_id",
                "student_id",
                "source_kind",
                "class_id",
                "teacher_id",
                "policy_version",
                "source_digest",
                "result_snapshot",
                "correct_count",
                "question_count",
                "score",
                "completed_at",
                "created_at",
            ),
            "indexes": (
                "CREATE INDEX ix_route_learning_result_class_completed ON "
                "route_learning_results (class_id, completed_at)",
                "CREATE INDEX ix_route_learning_result_student_completed ON "
                "route_learning_results (student_id, completed_at)",
            ),
            "table": "\n"
            "CREATE TABLE route_learning_results (\n"
            "\tid SERIAL NOT NULL, \n"
            "\tpublic_id VARCHAR(36) NOT NULL, \n"
            "\troute_id INTEGER NOT NULL, \n"
            "\tattempt_id INTEGER NOT NULL, \n"
            "\tstudent_id INTEGER NOT NULL, \n"
            "\tsource_kind VARCHAR(20) NOT NULL, \n"
            "\tclass_id INTEGER, \n"
            "\tteacher_id INTEGER, \n"
            "\tpolicy_version VARCHAR(80) NOT NULL, \n"
            "\tsource_digest VARCHAR(64) NOT NULL, \n"
            "\tresult_snapshot JSON NOT NULL, \n"
            "\tcorrect_count INTEGER NOT NULL, \n"
            "\tquestion_count INTEGER NOT NULL, \n"
            "\tscore NUMERIC(5, 1) NOT NULL, \n"
            "\tcompleted_at TIMESTAMP WITH TIME ZONE NOT NULL, \n"
            "\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_learning_result_public_id UNIQUE "
            "(public_id), \n"
            "\tCONSTRAINT uq_route_learning_result_route UNIQUE "
            "(route_id), \n"
            "\tCONSTRAINT uq_route_learning_result_attempt UNIQUE "
            "(attempt_id), \n"
            "\tCONSTRAINT ck_route_learning_result_source_kind CHECK "
            "(source_kind IN ('classroom', 'autonomous')), \n"
            "\tCONSTRAINT ck_route_learning_result_source_scope CHECK "
            "((source_kind = 'classroom' AND class_id IS NOT NULL AND "
            "teacher_id IS NOT NULL) OR (source_kind = 'autonomous' AND "
            "class_id IS NULL AND teacher_id IS NULL)), \n"
            "\tFOREIGN KEY(route_id) REFERENCES learning_routes (id) ON "
            "DELETE RESTRICT, \n"
            "\tFOREIGN KEY(attempt_id) REFERENCES route_test_attempts (id) "
            "ON DELETE RESTRICT, \n"
            "\tFOREIGN KEY(student_id) REFERENCES users (id) ON DELETE "
            "RESTRICT, \n"
            "\tFOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE "
            "RESTRICT, \n"
            "\tFOREIGN KEY(teacher_id) REFERENCES users (id) ON DELETE "
            "RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_reading_progress": {
            "columns": (
                "id",
                "step_id",
                "student_id",
                "active_lease_token",
                "active_lease_expires_at",
                "last_seen_at",
                "accumulated_seconds",
                "last_request_id",
                "last_request_digest",
                "updated_at",
            ),
            "indexes": ("CREATE INDEX ix_route_reading_student ON route_reading_progress (student_id)",),
            "table": "\n"
            "CREATE TABLE route_reading_progress (\n"
            "\tid SERIAL NOT NULL, \n"
            "\tstep_id INTEGER NOT NULL, \n"
            "\tstudent_id INTEGER NOT NULL, \n"
            "\tactive_lease_token VARCHAR(100), \n"
            "\tactive_lease_expires_at TIMESTAMP WITH TIME ZONE, \n"
            "\tlast_seen_at TIMESTAMP WITH TIME ZONE, \n"
            "\taccumulated_seconds INTEGER DEFAULT '0' NOT NULL, \n"
            "\tlast_request_id VARCHAR(100), \n"
            "\tlast_request_digest VARCHAR(64), \n"
            "\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_reading_step_student UNIQUE (step_id, "
            "student_id), \n"
            "\tCONSTRAINT ck_route_reading_accumulated_seconds CHECK "
            "(accumulated_seconds >= 0), \n"
            "\tFOREIGN KEY(step_id) REFERENCES learning_route_steps (id) ON "
            "DELETE RESTRICT, \n"
            "\tFOREIGN KEY(student_id) REFERENCES users (id) ON DELETE "
            "RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_test_attempts": {
            "columns": (
                "id",
                "public_id",
                "test_id",
                "student_id",
                "test_version",
                "test_digest",
                "draft_version",
                "answers",
                "status",
                "submission_id",
                "submission_digest",
                "correct_count",
                "question_count",
                "score",
                "submitted_at",
                "created_at",
                "updated_at",
            ),
            "indexes": ("CREATE INDEX ix_route_test_attempt_student ON route_test_attempts (student_id)",),
            "table": "\n"
            "CREATE TABLE route_test_attempts (\n"
            "\tid SERIAL NOT NULL, \n"
            "\tpublic_id VARCHAR(36) NOT NULL, \n"
            "\ttest_id INTEGER NOT NULL, \n"
            "\tstudent_id INTEGER NOT NULL, \n"
            "\ttest_version INTEGER NOT NULL, \n"
            "\ttest_digest VARCHAR(64) NOT NULL, \n"
            "\tdraft_version INTEGER DEFAULT '1' NOT NULL, \n"
            "\tanswers JSON DEFAULT '{}' NOT NULL, \n"
            "\tstatus VARCHAR(16) DEFAULT 'in_progress' NOT NULL, \n"
            "\tsubmission_id VARCHAR(100), \n"
            "\tsubmission_digest VARCHAR(64), \n"
            "\tcorrect_count INTEGER, \n"
            "\tquestion_count INTEGER, \n"
            "\tscore NUMERIC(5, 1), \n"
            "\tsubmitted_at TIMESTAMP WITH TIME ZONE, \n"
            "\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_test_attempt_public_id UNIQUE (public_id), \n"
            "\tCONSTRAINT uq_route_test_attempt_student UNIQUE (test_id, "
            "student_id), \n"
            "\tCONSTRAINT ck_route_test_attempt_draft_version CHECK "
            "(draft_version >= 1), \n"
            "\tCONSTRAINT ck_route_test_attempt_status CHECK (status IN "
            "('in_progress', 'submitted')), \n"
            "\tCONSTRAINT ck_route_test_attempt_correct_count CHECK "
            "(correct_count IS NULL OR correct_count >= 0), \n"
            "\tCONSTRAINT ck_route_test_attempt_question_count CHECK "
            "(question_count IS NULL OR question_count > 0), \n"
            "\tCONSTRAINT ck_route_test_attempt_score CHECK (score IS NULL OR "
            "(score >= 0 AND score <= 100)), \n"
            "\tCONSTRAINT ck_route_test_attempt_submission_fields CHECK "
            "((status = 'submitted' AND submission_id IS NOT NULL AND "
            "submission_digest IS NOT NULL AND correct_count IS NOT NULL AND "
            "question_count IS NOT NULL AND score IS NOT NULL AND submitted_at "
            "IS NOT NULL) OR status = 'in_progress'), \n"
            "\tFOREIGN KEY(test_id) REFERENCES route_final_tests (id) ON DELETE "
            "RESTRICT, \n"
            "\tFOREIGN KEY(student_id) REFERENCES users (id) ON DELETE "
            "RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_test_questions": {
            "columns": (
                "id",
                "public_id",
                "test_id",
                "stable_key",
                "position",
                "primary_point_code",
                "prompt",
                "options",
                "correct_option",
                "explanation",
                "private_grading",
            ),
            "indexes": (
                "CREATE INDEX ix_route_test_question_test_point ON route_test_questions (test_id, primary_point_code)",
            ),
            "table": "\n"
            "CREATE TABLE route_test_questions (\n"
            "\tid SERIAL NOT NULL, \n"
            "\tpublic_id VARCHAR(36) NOT NULL, \n"
            "\ttest_id INTEGER NOT NULL, \n"
            "\tstable_key VARCHAR(100) NOT NULL, \n"
            "\tposition INTEGER NOT NULL, \n"
            "\tprimary_point_code VARCHAR(120) NOT NULL, \n"
            "\tprompt TEXT NOT NULL, \n"
            "\toptions JSON NOT NULL, \n"
            "\tcorrect_option INTEGER NOT NULL, \n"
            "\texplanation TEXT DEFAULT '' NOT NULL, \n"
            "\tprivate_grading JSON DEFAULT '{}' NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_test_question_public_id UNIQUE "
            "(public_id), \n"
            "\tCONSTRAINT uq_route_test_question_stable_key UNIQUE (test_id, "
            "stable_key), \n"
            "\tCONSTRAINT uq_route_test_question_position UNIQUE (test_id, "
            "position), \n"
            "\tCONSTRAINT ck_route_test_question_position CHECK (position >= "
            "1), \n"
            "\tCONSTRAINT ck_route_test_question_correct_option CHECK "
            "(correct_option BETWEEN 0 AND 3), \n"
            "\tFOREIGN KEY(test_id) REFERENCES route_final_tests (id) ON "
            "DELETE RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_test_review_events": {
            "columns": ("id", "test_id", "teacher_id", "action", "version", "digest", "feedback", "created_at"),
            "indexes": (
                "CREATE INDEX ix_route_test_review_teacher_created ON "
                "route_test_review_events (teacher_id, created_at)",
            ),
            "table": "\n"
            "CREATE TABLE route_test_review_events (\n"
            "\tid SERIAL NOT NULL, \n"
            "\ttest_id INTEGER NOT NULL, \n"
            "\tteacher_id INTEGER NOT NULL, \n"
            "\taction VARCHAR(24) NOT NULL, \n"
            "\tversion INTEGER NOT NULL, \n"
            "\tdigest VARCHAR(64) NOT NULL, \n"
            "\tfeedback TEXT, \n"
            "\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT "
            "NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_test_review_version_action UNIQUE "
            "(test_id, version, action), \n"
            "\tCONSTRAINT ck_route_test_review_action CHECK (action IN "
            "('requested_changes', 'released')), \n"
            "\tCONSTRAINT ck_route_test_review_version CHECK (version >= "
            "1), \n"
            "\tCONSTRAINT ck_route_test_review_feedback_length CHECK "
            "(feedback IS NULL OR length(feedback) <= 1000), \n"
            "\tFOREIGN KEY(test_id) REFERENCES route_final_tests (id) ON "
            "DELETE RESTRICT, \n"
            "\tFOREIGN KEY(teacher_id) REFERENCES users (id) ON DELETE "
            "RESTRICT\n"
            ")\n"
            "\n",
        },
    },
    "sqlite": {
        "learning_route_steps": {
            "columns": (
                "id",
                "public_id",
                "route_id",
                "position",
                "kind",
                "title",
                "goal_point_codes",
                "source_snapshot",
                "public_definition",
                "private_definition",
                "status",
                "completed_at",
                "created_at",
                "updated_at",
            ),
            "indexes": (
                "CREATE INDEX ix_learning_route_steps_route_status ON learning_route_steps (route_id, status)",
            ),
            "table": "\n"
            "CREATE TABLE learning_route_steps (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpublic_id VARCHAR(36) NOT NULL, \n"
            "\troute_id INTEGER NOT NULL, \n"
            "\tposition INTEGER NOT NULL, \n"
            "\tkind VARCHAR(12) NOT NULL, \n"
            "\ttitle VARCHAR(200) DEFAULT '' NOT NULL, \n"
            "\tgoal_point_codes JSON DEFAULT '[]' NOT NULL, \n"
            "\tsource_snapshot JSON DEFAULT '{}' NOT NULL, \n"
            "\tpublic_definition JSON DEFAULT '{}' NOT NULL, \n"
            "\tprivate_definition JSON DEFAULT '{}' NOT NULL, \n"
            "\tstatus VARCHAR(16) DEFAULT 'locked' NOT NULL, \n"
            "\tcompleted_at DATETIME, \n"
            "\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tupdated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_learning_route_step_public_id UNIQUE (public_id), \n"
            "\tCONSTRAINT uq_learning_route_step_position UNIQUE (route_id, "
            "position), \n"
            "\tCONSTRAINT ck_learning_route_step_position CHECK (position >= 1), \n"
            "\tCONSTRAINT ck_learning_route_step_kind CHECK (kind IN ('reading', "
            "'case')), \n"
            "\tCONSTRAINT ck_learning_route_step_status CHECK (status IN "
            "('locked', 'available', 'in_progress', 'completed', 'blocked')), \n"
            "\tFOREIGN KEY(route_id) REFERENCES learning_routes (id) ON DELETE "
            "RESTRICT\n"
            ")\n"
            "\n",
        },
        "learning_routes": {
            "columns": (
                "id",
                "public_id",
                "student_id",
                "source_participation_id",
                "session_id",
                "completion_snapshot_id",
                "source_kind",
                "class_id",
                "teacher_id",
                "title",
                "goal_point_codes",
                "diagnosis_summary",
                "generation_context",
                "generation_state",
                "generation_claim_token",
                "generation_claim_expires_at",
                "generation_execution_state",
                "error_code",
                "content_version",
                "content_digest",
                "published_at",
                "route_completed_at",
                "created_at",
                "updated_at",
            ),
            "indexes": (
                "CREATE INDEX ix_learning_route_class_created ON learning_routes (class_id, created_at)",
                "CREATE INDEX ix_learning_route_student_created ON learning_routes (student_id, created_at)",
            ),
            "table": "\n"
            "CREATE TABLE learning_routes (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpublic_id VARCHAR(36) NOT NULL, \n"
            "\tstudent_id INTEGER NOT NULL, \n"
            "\tsource_participation_id INTEGER NOT NULL, \n"
            "\tsession_id INTEGER NOT NULL, \n"
            "\tcompletion_snapshot_id INTEGER NOT NULL, \n"
            "\tsource_kind VARCHAR(20) NOT NULL, \n"
            "\tclass_id INTEGER, \n"
            "\tteacher_id INTEGER, \n"
            "\ttitle VARCHAR(200) DEFAULT '学习计划' NOT NULL, \n"
            "\tgoal_point_codes JSON DEFAULT '[]' NOT NULL, \n"
            "\tdiagnosis_summary JSON DEFAULT '{}' NOT NULL, \n"
            "\tgeneration_context JSON DEFAULT '{}' NOT NULL, \n"
            "\tgeneration_state VARCHAR(24) DEFAULT 'pending' NOT NULL, \n"
            "\tgeneration_claim_token VARCHAR(100), \n"
            "\tgeneration_claim_expires_at DATETIME, \n"
            "\tgeneration_execution_state VARCHAR(12), \n"
            "\terror_code VARCHAR(80), \n"
            "\tcontent_version INTEGER, \n"
            "\tcontent_digest VARCHAR(64), \n"
            "\tpublished_at DATETIME, \n"
            "\troute_completed_at DATETIME, \n"
            "\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tupdated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_learning_route_participation UNIQUE "
            "(source_participation_id), \n"
            "\tCONSTRAINT uq_learning_route_public_id UNIQUE (public_id), \n"
            "\tCONSTRAINT ck_learning_route_source_kind CHECK (source_kind IN "
            "('classroom', 'autonomous')), \n"
            "\tCONSTRAINT ck_learning_route_generation_state CHECK (generation_state IN "
            "('pending', 'generating', 'published', 'generation_failed')), \n"
            "\tCONSTRAINT ck_learning_route_source_scope CHECK ((source_kind = "
            "'classroom' AND class_id IS NOT NULL AND teacher_id IS NOT NULL) OR "
            "(source_kind = 'autonomous' AND class_id IS NULL AND teacher_id IS "
            "NULL)), \n"
            "\tCONSTRAINT ck_learning_route_content_version CHECK (content_version IS "
            "NULL OR content_version >= 1), \n"
            "\tFOREIGN KEY(student_id) REFERENCES users (id) ON DELETE RESTRICT, \n"
            "\tFOREIGN KEY(source_participation_id) REFERENCES pbl_participations (id) "
            "ON DELETE RESTRICT, \n"
            "\tFOREIGN KEY(session_id) REFERENCES pbl_sessions (id) ON DELETE "
            "RESTRICT, \n"
            "\tFOREIGN KEY(completion_snapshot_id) REFERENCES pbl_diagnostic_snapshots "
            "(id) ON DELETE RESTRICT, \n"
            "\tFOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE RESTRICT, \n"
            "\tFOREIGN KEY(teacher_id) REFERENCES users (id) ON DELETE RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_case_messages": {
            "columns": (
                "id",
                "case_session_id",
                "sequence",
                "role",
                "content",
                "client_message_id",
                "request_revision",
                "processing_status",
                "processing_token",
                "processing_expires_at",
                "payload_digest",
                "error_code",
                "created_at",
                "updated_at",
            ),
            "indexes": (
                "CREATE INDEX ix_route_case_message_session_revision ON "
                "route_case_messages (case_session_id, request_revision)",
            ),
            "table": "\n"
            "CREATE TABLE route_case_messages (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tcase_session_id INTEGER NOT NULL, \n"
            "\tsequence INTEGER NOT NULL, \n"
            "\trole VARCHAR(12) NOT NULL, \n"
            "\tcontent TEXT NOT NULL, \n"
            "\tclient_message_id VARCHAR(100), \n"
            "\trequest_revision INTEGER NOT NULL, \n"
            "\tprocessing_status VARCHAR(16) DEFAULT 'completed' NOT NULL, \n"
            "\tprocessing_token VARCHAR(100), \n"
            "\tprocessing_expires_at DATETIME, \n"
            "\tpayload_digest VARCHAR(64), \n"
            "\terror_code VARCHAR(80), \n"
            "\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tupdated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_case_message_sequence UNIQUE (case_session_id, "
            "sequence), \n"
            "\tCONSTRAINT uq_route_case_message_client_id UNIQUE (case_session_id, "
            "client_message_id), \n"
            "\tCONSTRAINT ck_route_case_message_sequence CHECK (sequence >= 1), \n"
            "\tCONSTRAINT ck_route_case_message_role CHECK (role IN ('student', "
            "'assistant')), \n"
            "\tCONSTRAINT ck_route_case_message_processing_status CHECK "
            "(processing_status IN ('pending', 'processing', 'completed', 'failed', "
            "'blocked')), \n"
            "\tCONSTRAINT ck_route_case_message_revision CHECK (request_revision >= "
            "1), \n"
            "\tFOREIGN KEY(case_session_id) REFERENCES route_case_sessions (id) ON "
            "DELETE RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_case_phase_decisions": {
            "columns": (
                "id",
                "case_session_id",
                "message_id",
                "revision",
                "phase",
                "decision",
                "evidence_message_ids",
                "satisfied_goal_codes",
                "missing_goal_codes",
                "safety_status",
                "created_at",
            ),
            "indexes": (),
            "table": "\n"
            "CREATE TABLE route_case_phase_decisions (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tcase_session_id INTEGER NOT NULL, \n"
            "\tmessage_id INTEGER NOT NULL, \n"
            "\trevision INTEGER NOT NULL, \n"
            "\tphase VARCHAR(32) NOT NULL, \n"
            "\tdecision VARCHAR(12) NOT NULL, \n"
            "\tevidence_message_ids JSON DEFAULT '[]' NOT NULL, \n"
            "\tsatisfied_goal_codes JSON DEFAULT '[]' NOT NULL, \n"
            "\tmissing_goal_codes JSON DEFAULT '[]' NOT NULL, \n"
            "\tsafety_status VARCHAR(12) NOT NULL, \n"
            "\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_case_decision_revision UNIQUE "
            "(case_session_id, revision), \n"
            "\tCONSTRAINT uq_route_case_decision_message UNIQUE "
            "(message_id), \n"
            "\tCONSTRAINT ck_route_case_decision_phase CHECK (phase IN "
            "('pathology_recognition', 'mechanism_explanation', "
            "'evidence_judgment')), \n"
            "\tCONSTRAINT ck_route_case_decision_value CHECK (decision IN "
            "('stay', 'advance', 'complete')), \n"
            "\tCONSTRAINT ck_route_case_decision_safety CHECK (safety_status "
            "IN ('educational', 'unsafe')), \n"
            "\tFOREIGN KEY(case_session_id) REFERENCES route_case_sessions "
            "(id) ON DELETE RESTRICT, \n"
            "\tFOREIGN KEY(message_id) REFERENCES route_case_messages (id) "
            "ON DELETE RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_case_sessions": {
            "columns": (
                "id",
                "public_id",
                "step_id",
                "student_id",
                "phase",
                "revision",
                "phase_started_revision",
                "status",
                "completed_at",
                "created_at",
                "updated_at",
            ),
            "indexes": (),
            "table": "\n"
            "CREATE TABLE route_case_sessions (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpublic_id VARCHAR(36) NOT NULL, \n"
            "\tstep_id INTEGER NOT NULL, \n"
            "\tstudent_id INTEGER NOT NULL, \n"
            "\tphase VARCHAR(32) DEFAULT 'pathology_recognition' NOT NULL, \n"
            "\trevision INTEGER DEFAULT '0' NOT NULL, \n"
            "\tphase_started_revision INTEGER DEFAULT '0' NOT NULL, \n"
            "\tstatus VARCHAR(16) DEFAULT 'in_progress' NOT NULL, \n"
            "\tcompleted_at DATETIME, \n"
            "\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tupdated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_case_session_public_id UNIQUE (public_id), \n"
            "\tCONSTRAINT uq_route_case_session_step UNIQUE (step_id), \n"
            "\tCONSTRAINT ck_route_case_session_phase CHECK (phase IN "
            "('pathology_recognition', 'mechanism_explanation', "
            "'evidence_judgment', 'completed')), \n"
            "\tCONSTRAINT ck_route_case_session_revision CHECK (revision >= 0), \n"
            "\tCONSTRAINT ck_route_case_session_phase_revision CHECK "
            "(phase_started_revision >= 0), \n"
            "\tCONSTRAINT ck_route_case_session_status CHECK (status IN "
            "('in_progress', 'blocked', 'completed')), \n"
            "\tFOREIGN KEY(step_id) REFERENCES learning_route_steps (id) ON DELETE "
            "RESTRICT, \n"
            "\tFOREIGN KEY(student_id) REFERENCES users (id) ON DELETE RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_command_receipts": {
            "columns": (
                "id",
                "actor_id",
                "operation",
                "client_request_id",
                "payload_digest",
                "resource_kind",
                "resource_public_id",
                "result_version",
                "response_locator",
                "response_snapshot",
                "created_at",
            ),
            "indexes": (
                "CREATE INDEX ix_route_command_receipt_resource ON route_command_receipts (resource_public_id)",
            ),
            "table": "\n"
            "CREATE TABLE route_command_receipts (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tactor_id INTEGER NOT NULL, \n"
            "\toperation VARCHAR(60) NOT NULL, \n"
            "\tclient_request_id VARCHAR(100) NOT NULL, \n"
            "\tpayload_digest VARCHAR(64) NOT NULL, \n"
            "\tresource_kind VARCHAR(40) NOT NULL, \n"
            "\tresource_public_id VARCHAR(36) NOT NULL, \n"
            "\tresult_version INTEGER NOT NULL, \n"
            "\tresponse_locator VARCHAR(200), \n"
            "\tresponse_snapshot JSON, \n"
            "\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_command_request UNIQUE (actor_id, operation, "
            "client_request_id), \n"
            "\tCONSTRAINT ck_route_command_receipt_result_version CHECK "
            "(result_version >= 1), \n"
            "\tFOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_final_tests": {
            "columns": (
                "id",
                "public_id",
                "title",
                "route_id",
                "generation_state",
                "generation_claim_token",
                "generation_claim_expires_at",
                "generation_execution_state",
                "error_code",
                "review_state",
                "review_kind",
                "feedback_draft",
                "version",
                "draft_digest",
                "released_version",
                "released_digest",
                "released_at",
                "reviewer_id",
                "created_at",
                "updated_at",
            ),
            "indexes": ("CREATE INDEX ix_route_final_test_generation_state ON route_final_tests (generation_state)",),
            "table": "\n"
            "CREATE TABLE route_final_tests (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpublic_id VARCHAR(36) NOT NULL, \n"
            "\ttitle VARCHAR(200) DEFAULT '最终测试' NOT NULL, \n"
            "\troute_id INTEGER NOT NULL, \n"
            "\tgeneration_state VARCHAR(24) DEFAULT 'pending' NOT NULL, \n"
            "\tgeneration_claim_token VARCHAR(100), \n"
            "\tgeneration_claim_expires_at DATETIME, \n"
            "\tgeneration_execution_state VARCHAR(12), \n"
            "\terror_code VARCHAR(80), \n"
            "\treview_state VARCHAR(20) DEFAULT 'pending_review' NOT NULL, \n"
            "\treview_kind VARCHAR(12) DEFAULT 'teacher' NOT NULL, \n"
            "\tfeedback_draft TEXT DEFAULT '' NOT NULL, \n"
            "\tversion INTEGER DEFAULT '1' NOT NULL, \n"
            "\tdraft_digest VARCHAR(64), \n"
            "\treleased_version INTEGER, \n"
            "\treleased_digest VARCHAR(64), \n"
            "\treleased_at DATETIME, \n"
            "\treviewer_id INTEGER, \n"
            "\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tupdated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_final_test_public_id UNIQUE (public_id), \n"
            "\tCONSTRAINT uq_route_final_test_route UNIQUE (route_id), \n"
            "\tCONSTRAINT ck_route_final_test_generation_state CHECK "
            "(generation_state IN ('pending', 'generating', 'ready', "
            "'generation_failed')), \n"
            "\tCONSTRAINT ck_route_final_test_review_state CHECK (review_state IN "
            "('pending_review', 'needs_changes', 'released')), \n"
            "\tCONSTRAINT ck_route_final_test_review_kind CHECK (review_kind IN "
            "('teacher', 'ai_direct')), \n"
            "\tCONSTRAINT ck_route_final_test_version CHECK (version >= 1), \n"
            "\tCONSTRAINT ck_route_final_test_released_version CHECK "
            "(released_version IS NULL OR released_version >= 1), \n"
            "\tCONSTRAINT ck_route_final_test_reviewer_scope CHECK ((review_kind = "
            "'ai_direct' AND reviewer_id IS NULL AND review_state = 'released') OR "
            "(review_kind = 'teacher' AND (review_state != 'released' OR reviewer_id "
            "IS NOT NULL))), \n"
            "\tFOREIGN KEY(route_id) REFERENCES learning_routes (id) ON DELETE "
            "RESTRICT, \n"
            "\tFOREIGN KEY(reviewer_id) REFERENCES users (id) ON DELETE RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_learning_results": {
            "columns": (
                "id",
                "public_id",
                "route_id",
                "attempt_id",
                "student_id",
                "source_kind",
                "class_id",
                "teacher_id",
                "policy_version",
                "source_digest",
                "result_snapshot",
                "correct_count",
                "question_count",
                "score",
                "completed_at",
                "created_at",
            ),
            "indexes": (
                "CREATE INDEX ix_route_learning_result_class_completed ON "
                "route_learning_results (class_id, completed_at)",
                "CREATE INDEX ix_route_learning_result_student_completed ON "
                "route_learning_results (student_id, completed_at)",
            ),
            "table": "\n"
            "CREATE TABLE route_learning_results (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpublic_id VARCHAR(36) NOT NULL, \n"
            "\troute_id INTEGER NOT NULL, \n"
            "\tattempt_id INTEGER NOT NULL, \n"
            "\tstudent_id INTEGER NOT NULL, \n"
            "\tsource_kind VARCHAR(20) NOT NULL, \n"
            "\tclass_id INTEGER, \n"
            "\tteacher_id INTEGER, \n"
            "\tpolicy_version VARCHAR(80) NOT NULL, \n"
            "\tsource_digest VARCHAR(64) NOT NULL, \n"
            "\tresult_snapshot JSON NOT NULL, \n"
            "\tcorrect_count INTEGER NOT NULL, \n"
            "\tquestion_count INTEGER NOT NULL, \n"
            "\tscore NUMERIC(5, 1) NOT NULL, \n"
            "\tcompleted_at DATETIME NOT NULL, \n"
            "\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_learning_result_public_id UNIQUE "
            "(public_id), \n"
            "\tCONSTRAINT uq_route_learning_result_route UNIQUE (route_id), \n"
            "\tCONSTRAINT uq_route_learning_result_attempt UNIQUE "
            "(attempt_id), \n"
            "\tCONSTRAINT ck_route_learning_result_source_kind CHECK "
            "(source_kind IN ('classroom', 'autonomous')), \n"
            "\tCONSTRAINT ck_route_learning_result_source_scope CHECK "
            "((source_kind = 'classroom' AND class_id IS NOT NULL AND teacher_id "
            "IS NOT NULL) OR (source_kind = 'autonomous' AND class_id IS NULL "
            "AND teacher_id IS NULL)), \n"
            "\tFOREIGN KEY(route_id) REFERENCES learning_routes (id) ON DELETE "
            "RESTRICT, \n"
            "\tFOREIGN KEY(attempt_id) REFERENCES route_test_attempts (id) ON "
            "DELETE RESTRICT, \n"
            "\tFOREIGN KEY(student_id) REFERENCES users (id) ON DELETE "
            "RESTRICT, \n"
            "\tFOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE "
            "RESTRICT, \n"
            "\tFOREIGN KEY(teacher_id) REFERENCES users (id) ON DELETE RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_reading_progress": {
            "columns": (
                "id",
                "step_id",
                "student_id",
                "active_lease_token",
                "active_lease_expires_at",
                "last_seen_at",
                "accumulated_seconds",
                "last_request_id",
                "last_request_digest",
                "updated_at",
            ),
            "indexes": ("CREATE INDEX ix_route_reading_student ON route_reading_progress (student_id)",),
            "table": "\n"
            "CREATE TABLE route_reading_progress (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tstep_id INTEGER NOT NULL, \n"
            "\tstudent_id INTEGER NOT NULL, \n"
            "\tactive_lease_token VARCHAR(100), \n"
            "\tactive_lease_expires_at DATETIME, \n"
            "\tlast_seen_at DATETIME, \n"
            "\taccumulated_seconds INTEGER DEFAULT '0' NOT NULL, \n"
            "\tlast_request_id VARCHAR(100), \n"
            "\tlast_request_digest VARCHAR(64), \n"
            "\tupdated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_reading_step_student UNIQUE (step_id, "
            "student_id), \n"
            "\tCONSTRAINT ck_route_reading_accumulated_seconds CHECK "
            "(accumulated_seconds >= 0), \n"
            "\tFOREIGN KEY(step_id) REFERENCES learning_route_steps (id) ON "
            "DELETE RESTRICT, \n"
            "\tFOREIGN KEY(student_id) REFERENCES users (id) ON DELETE RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_test_attempts": {
            "columns": (
                "id",
                "public_id",
                "test_id",
                "student_id",
                "test_version",
                "test_digest",
                "draft_version",
                "answers",
                "status",
                "submission_id",
                "submission_digest",
                "correct_count",
                "question_count",
                "score",
                "submitted_at",
                "created_at",
                "updated_at",
            ),
            "indexes": ("CREATE INDEX ix_route_test_attempt_student ON route_test_attempts (student_id)",),
            "table": "\n"
            "CREATE TABLE route_test_attempts (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpublic_id VARCHAR(36) NOT NULL, \n"
            "\ttest_id INTEGER NOT NULL, \n"
            "\tstudent_id INTEGER NOT NULL, \n"
            "\ttest_version INTEGER NOT NULL, \n"
            "\ttest_digest VARCHAR(64) NOT NULL, \n"
            "\tdraft_version INTEGER DEFAULT '1' NOT NULL, \n"
            "\tanswers JSON DEFAULT '{}' NOT NULL, \n"
            "\tstatus VARCHAR(16) DEFAULT 'in_progress' NOT NULL, \n"
            "\tsubmission_id VARCHAR(100), \n"
            "\tsubmission_digest VARCHAR(64), \n"
            "\tcorrect_count INTEGER, \n"
            "\tquestion_count INTEGER, \n"
            "\tscore NUMERIC(5, 1), \n"
            "\tsubmitted_at DATETIME, \n"
            "\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tupdated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_test_attempt_public_id UNIQUE (public_id), \n"
            "\tCONSTRAINT uq_route_test_attempt_student UNIQUE (test_id, "
            "student_id), \n"
            "\tCONSTRAINT ck_route_test_attempt_draft_version CHECK (draft_version "
            ">= 1), \n"
            "\tCONSTRAINT ck_route_test_attempt_status CHECK (status IN "
            "('in_progress', 'submitted')), \n"
            "\tCONSTRAINT ck_route_test_attempt_correct_count CHECK (correct_count "
            "IS NULL OR correct_count >= 0), \n"
            "\tCONSTRAINT ck_route_test_attempt_question_count CHECK "
            "(question_count IS NULL OR question_count > 0), \n"
            "\tCONSTRAINT ck_route_test_attempt_score CHECK (score IS NULL OR "
            "(score >= 0 AND score <= 100)), \n"
            "\tCONSTRAINT ck_route_test_attempt_submission_fields CHECK ((status = "
            "'submitted' AND submission_id IS NOT NULL AND submission_digest IS NOT "
            "NULL AND correct_count IS NOT NULL AND question_count IS NOT NULL AND "
            "score IS NOT NULL AND submitted_at IS NOT NULL) OR status = "
            "'in_progress'), \n"
            "\tFOREIGN KEY(test_id) REFERENCES route_final_tests (id) ON DELETE "
            "RESTRICT, \n"
            "\tFOREIGN KEY(student_id) REFERENCES users (id) ON DELETE RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_test_questions": {
            "columns": (
                "id",
                "public_id",
                "test_id",
                "stable_key",
                "position",
                "primary_point_code",
                "prompt",
                "options",
                "correct_option",
                "explanation",
                "private_grading",
            ),
            "indexes": (
                "CREATE INDEX ix_route_test_question_test_point ON route_test_questions (test_id, primary_point_code)",
            ),
            "table": "\n"
            "CREATE TABLE route_test_questions (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpublic_id VARCHAR(36) NOT NULL, \n"
            "\ttest_id INTEGER NOT NULL, \n"
            "\tstable_key VARCHAR(100) NOT NULL, \n"
            "\tposition INTEGER NOT NULL, \n"
            "\tprimary_point_code VARCHAR(120) NOT NULL, \n"
            "\tprompt TEXT NOT NULL, \n"
            "\toptions JSON NOT NULL, \n"
            "\tcorrect_option INTEGER NOT NULL, \n"
            "\texplanation TEXT DEFAULT '' NOT NULL, \n"
            "\tprivate_grading JSON DEFAULT '{}' NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_test_question_public_id UNIQUE (public_id), \n"
            "\tCONSTRAINT uq_route_test_question_stable_key UNIQUE (test_id, "
            "stable_key), \n"
            "\tCONSTRAINT uq_route_test_question_position UNIQUE (test_id, "
            "position), \n"
            "\tCONSTRAINT ck_route_test_question_position CHECK (position >= 1), \n"
            "\tCONSTRAINT ck_route_test_question_correct_option CHECK "
            "(correct_option BETWEEN 0 AND 3), \n"
            "\tFOREIGN KEY(test_id) REFERENCES route_final_tests (id) ON DELETE "
            "RESTRICT\n"
            ")\n"
            "\n",
        },
        "route_test_review_events": {
            "columns": ("id", "test_id", "teacher_id", "action", "version", "digest", "feedback", "created_at"),
            "indexes": (
                "CREATE INDEX ix_route_test_review_teacher_created ON "
                "route_test_review_events (teacher_id, created_at)",
            ),
            "table": "\n"
            "CREATE TABLE route_test_review_events (\n"
            "\tid INTEGER NOT NULL, \n"
            "\ttest_id INTEGER NOT NULL, \n"
            "\tteacher_id INTEGER NOT NULL, \n"
            "\taction VARCHAR(24) NOT NULL, \n"
            "\tversion INTEGER NOT NULL, \n"
            "\tdigest VARCHAR(64) NOT NULL, \n"
            "\tfeedback TEXT, \n"
            "\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tCONSTRAINT uq_route_test_review_version_action UNIQUE (test_id, "
            "version, action), \n"
            "\tCONSTRAINT ck_route_test_review_action CHECK (action IN "
            "('requested_changes', 'released')), \n"
            "\tCONSTRAINT ck_route_test_review_version CHECK (version >= 1), \n"
            "\tCONSTRAINT ck_route_test_review_feedback_length CHECK (feedback "
            "IS NULL OR length(feedback) <= 1000), \n"
            "\tFOREIGN KEY(test_id) REFERENCES route_final_tests (id) ON "
            "DELETE RESTRICT, \n"
            "\tFOREIGN KEY(teacher_id) REFERENCES users (id) ON DELETE "
            "RESTRICT\n"
            ")\n"
            "\n",
        },
    },
}


def _ensure_route_tables() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect not in FROZEN_ROUTE_SCHEMA:
        raise RuntimeError(f"0033 has no frozen route DDL for dialect {dialect}")
    existing = _tables()
    for name in ROUTE_TABLE_NAMES:
        frozen = FROZEN_ROUTE_SCHEMA[dialect][name]
        if name in existing:
            count = bind.scalar(sa.text(f"SELECT COUNT(*) FROM {name}")) or 0
            if count:
                raise RuntimeError(f"0033 refuses pre-existing T44 data in {name}")
            actual_columns = {column["name"] for column in sa.inspect(bind).get_columns(name)}
            if actual_columns != set(frozen["columns"]):
                raise RuntimeError(f"0033 refuses an incompatible pre-existing table {name}")
            continue
        op.execute(frozen["table"])
        for statement in frozen["indexes"]:
            op.execute(statement)


def _detach_bank_sources() -> None:
    tables = _tables()
    required = {"teacher_question_bank_revisions", "bank_import_receipts", "classroom_package_items"}
    if not required.issubset(tables):
        return
    bind = op.get_bind()
    for table in ("teacher_question_bank_revisions", "bank_import_receipts"):
        columns = _columns(table)
        if "source_kind" not in columns:
            op.add_column(table, sa.Column("source_kind", sa.String(30), nullable=True))
        if "source_public_id" not in columns:
            op.add_column(table, sa.Column("source_public_id", sa.String(36), nullable=True))

    item_ids: set[int] = set()
    for table in ("teacher_question_bank_revisions", "bank_import_receipts"):
        if "source_package_item_id" in _columns(table):
            item_ids.update(
                int(value)
                for value in bind.execute(
                    sa.text(
                        f"SELECT DISTINCT source_package_item_id FROM {table} WHERE source_package_item_id IS NOT NULL"
                    )
                ).scalars()
            )
    source_ids = {item_id: str(uuid4()) for item_id in item_ids}
    for table in ("teacher_question_bank_revisions", "bank_import_receipts"):
        if "source_package_item_id" not in _columns(table):
            continue
        for item_id, public_id in source_ids.items():
            bind.execute(
                sa.text(
                    f"UPDATE {table} SET source_kind = 'legacy_detached', source_public_id = :public_id "
                    "WHERE source_package_item_id = :item_id"
                ),
                {"public_id": public_id, "item_id": item_id},
            )
        # Tables created from current metadata may already have the new source
        # columns and contain no old rows. New inserts require a detached id.
        if table == "bank_import_receipts" and "uq_bank_import_public_source" not in {
            item["name"] for item in sa.inspect(bind).get_unique_constraints(table)
        }:
            with op.batch_alter_table(table) as batch:
                batch.create_unique_constraint(
                    "uq_bank_import_public_source",
                    ["teacher_id", "source_kind", "source_public_id", "source_digest"],
                )
    # Drop the package-item foreign keys while leaving the legacy numeric value
    # nullable for request receipt replay until 0034 removes it completely.
    convention = {
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
    for table in ("teacher_question_bank_revisions", "bank_import_receipts"):
        fks = sa.inspect(bind).get_foreign_keys(table)
        for fk in fks:
            if (
                fk.get("constrained_columns") == ["source_package_item_id"]
                and fk.get("referred_table") == "classroom_package_items"
            ):
                name = fk.get("name") or (f"fk_{table}_source_package_item_id_classroom_package_items")
                with op.batch_alter_table(table, naming_convention=convention) as batch:
                    batch.drop_constraint(name, type_="foreignkey")
                    batch.alter_column(
                        "source_package_item_id",
                        existing_type=sa.Integer(),
                        nullable=True,
                    )
                break
        else:
            if "source_package_item_id" in _columns(table):
                with op.batch_alter_table(table, naming_convention=convention) as batch:
                    batch.alter_column(
                        "source_package_item_id",
                        existing_type=sa.Integer(),
                        nullable=True,
                    )
        # Promote source identity after all old rows have been assigned UUIDs.
        if "source_kind" in _columns(table) and "source_public_id" in _columns(table):
            with op.batch_alter_table(table, naming_convention=convention) as batch:
                batch.alter_column("source_kind", existing_type=sa.String(30), nullable=False)
                batch.alter_column("source_public_id", existing_type=sa.String(36), nullable=False)


def _create_cutover_tables() -> None:
    if "t44_cutover_manifests" not in _tables():
        op.create_table(
            "t44_cutover_manifests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("cutover_token", sa.String(100), nullable=False, unique=True),
            sa.Column("target_resource_digest", sa.String(64), nullable=False),
            sa.Column("original_head", sa.String(40), nullable=False),
            sa.Column("planned_delete_counts", sa.JSON(), nullable=False),
            sa.Column("retained_digest", sa.JSON(), nullable=False),
            sa.Column("id_high_water", sa.JSON(), nullable=False),
            sa.Column("target_ids", sa.JSON(), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if "t44_legacy_id_high_water" not in _tables():
        op.create_table(
            "t44_legacy_id_high_water",
            sa.Column("table_name", sa.String(80), primary_key=True),
            sa.Column("max_id", sa.Integer(), nullable=False),
        )
    bind = op.get_bind()
    for table in ("pbl_sessions", "pbl_participations", "pbl_diagnostic_snapshots"):
        if table not in _tables():
            continue
        max_id = bind.scalar(sa.text(f"SELECT COALESCE(MAX(id), 0) FROM {table}")) or 0
        current = bind.scalar(
            sa.text("SELECT max_id FROM t44_legacy_id_high_water WHERE table_name = :table"),
            {"table": table},
        )
        if current is None:
            bind.execute(
                sa.text("INSERT INTO t44_legacy_id_high_water (table_name, max_id) VALUES (:table, :max_id)"),
                {"table": table, "max_id": int(max_id)},
            )
        elif int(current) < int(max_id):
            bind.execute(
                sa.text("UPDATE t44_legacy_id_high_water SET max_id = :max_id WHERE table_name = :table"),
                {"table": table, "max_id": int(max_id)},
            )


def _prepare_notification_public_locator() -> None:
    if "student_notifications" in _tables() and "entity_public_id" not in _columns("student_notifications"):
        op.add_column("student_notifications", sa.Column("entity_public_id", sa.String(36), nullable=True))


def _prepare_pbl_schema_version() -> None:
    if "pbl_sessions" not in _tables() or "ai_schema_version" not in _columns("pbl_sessions"):
        return
    bind = op.get_bind()
    checks = {item["name"]: item.get("sqltext", "") for item in sa.inspect(bind).get_check_constraints("pbl_sessions")}
    current = checks.get("ck_pbl_session_ai_schema_version", "")
    widened = current.replace(" ", "").lower().endswith("in(6,7,8)")
    session_sql = (
        bind.execute(sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name='pbl_sessions'")).scalar()
        if bind.dialect.name == "sqlite"
        else None
    )
    session_needs_autoincrement = (
        bind.dialect.name == "sqlite" and "AUTOINCREMENT" not in str(session_sql or "").upper()
    )
    if widened and not session_needs_autoincrement:
        return
    table_kwargs = {"sqlite_autoincrement": True} if bind.dialect.name == "sqlite" else {}
    with op.batch_alter_table("pbl_sessions", table_kwargs=table_kwargs) as batch:
        if not widened and "ck_pbl_session_ai_schema_version" in checks:
            batch.drop_constraint("ck_pbl_session_ai_schema_version", type_="check")
        batch.alter_column(
            "ai_schema_version",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default="8",
        )
        if not widened:
            batch.create_check_constraint("ck_pbl_session_ai_schema_version", "ai_schema_version IN (6, 7, 8)")
        if session_needs_autoincrement:
            batch.alter_column("id", existing_type=sa.Integer(), existing_nullable=False, nullable=False)


def _ensure_sqlite_autoincrement(table: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite" or table not in _tables():
        return
    ddl = bind.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:table"), {"table": table}
    ).scalar()
    if "AUTOINCREMENT" in str(ddl or "").upper():
        return
    with op.batch_alter_table(table, table_kwargs={"sqlite_autoincrement": True}) as batch:
        batch.alter_column("id", existing_type=sa.Integer(), existing_nullable=False, nullable=False)


def upgrade() -> None:
    _ensure_route_tables()
    _detach_bank_sources()
    _create_cutover_tables()
    _prepare_notification_public_locator()
    _prepare_pbl_schema_version()
    _ensure_sqlite_autoincrement("pbl_participations")
    _ensure_sqlite_autoincrement("pbl_diagnostic_snapshots")


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        "route_test_review_events",
        "route_learning_results",
        "route_test_attempts",
        "route_test_questions",
        "route_final_tests",
        "route_case_phase_decisions",
        "route_case_messages",
        "route_case_sessions",
        "route_reading_progress",
        "learning_route_steps",
        "route_command_receipts",
        "learning_routes",
    ):
        if table in _tables() and bind.scalar(sa.text(f"SELECT COUNT(*) FROM {table}")):
            raise RuntimeError("Cannot downgrade 0033 while T44 learning data exists")
    raise RuntimeError("0033 source detachment is irreversible; restore a verified pre-0033 backup")
