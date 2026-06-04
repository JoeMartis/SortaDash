#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# End-to-end Tutor smoke test for course-inventory.
#
# What it does, in order:
#   1. Builds the openedx image with the plugin pip-installed.
#   2. Launches the Tutor stack (local mode, in detached form).
#   3. Runs the plugin's migrations.
#   4. Creates a staff superuser and a couple of fake courses.
#   5. Hits /course-inventory/ with the staff session cookie and
#      asserts:
#        - HTTP 200
#        - The seeded course display name appears in the HTML
#        - The HTMX bundle is served from same-origin
#        - The CSV export endpoint returns a streaming CSV
#   6. Reports pass/fail and tears the stack down on success.
#
# Requires: tutor, docker, jq, curl. Expects to be run on a machine
# with at least 8 GB RAM and ~20 GB of disk for the openedx image.
#
# Usage:
#   ./scripts/tutor_smoke.sh                  # build, launch, test, teardown
#   KEEP_RUNNING=1 ./scripts/tutor_smoke.sh   # don't tear down at the end
#   PLUGIN_SOURCE=git ./scripts/tutor_smoke.sh   # install from PyPI/git instead of local

set -euo pipefail

# ---- config ----------------------------------------------------------------

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_SOURCE="${PLUGIN_SOURCE:-local}"           # "local" or "git"
STUDIO_HOST="${STUDIO_HOST:-studio.local.openedx.io}"
STAFF_USER="${STAFF_USER:-ci-smoke-staff}"
STAFF_PASS="${STAFF_PASS:-smoke-password-not-secret}"
COURSE_KEY="${COURSE_KEY:-course-v1:edX+SMOKE+2026}"
COURSE_NAME="${COURSE_NAME:-Smoke Test Course}"
KEEP_RUNNING="${KEEP_RUNNING:-0}"

# ---- helpers ---------------------------------------------------------------

log() { printf '\033[1;34m[smoke]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[smoke ERROR]\033[0m %s\n' "$*" >&2; }
fail() { err "$*"; exit 1; }

cleanup() {
    local rc=$?
    if [[ $rc -ne 0 ]]; then
        err "smoke test failed (rc=$rc); leaving stack up for inspection"
        err "to tear down manually: tutor local stop"
    elif [[ "${KEEP_RUNNING}" == "1" ]]; then
        log "KEEP_RUNNING=1 set; leaving stack up"
    else
        log "tearing down Tutor stack"
        tutor local stop || true
    fi
}
trap cleanup EXIT

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || fail "$1 not found on PATH"
}

# ---- preflight -------------------------------------------------------------

require_cmd tutor
require_cmd docker
require_cmd curl
require_cmd jq
require_cmd git

log "running from ${REPO_ROOT}"
log "PLUGIN_SOURCE=${PLUGIN_SOURCE}"
log "Studio host: ${STUDIO_HOST}"

# ---- step 1: configure Tutor + install our plugin --------------------------

log "step 1/6 — configuring Tutor"

case "${PLUGIN_SOURCE}" in
    local)
        # Install the Tutor companion plugin from the working tree on
        # the host (this is what handles the openedx Dockerfile patch).
        pip install -e "${REPO_ROOT}/tutor-plugin"

        # Install the CMS plugin from the working tree's current commit
        # via git+https. We tried a wheel-staging approach previously,
        # but Tutor's python-requirements Dockerfile stage doesn't
        # blanket-COPY ./requirements/, so files dropped there don't
        # land at /openedx/requirements/ inside the build container.
        #
        # git+https sidesteps the build-context problem entirely: pip
        # clones the public repo at the exact SHA on the host. Requires
        # the repo to be public (which it is) so no auth is needed.
        REMOTE_URL=$(git -C "${REPO_ROOT}" config --get remote.origin.url)
        # Normalize SSH URL to HTTPS form for pip.
        REMOTE_URL=${REMOTE_URL/git@github.com:/https:\/\/github.com\/}
        REMOTE_URL=${REMOTE_URL%.git}
        SHA=$(git -C "${REPO_ROOT}" rev-parse HEAD)
        log "  installing course-inventory from ${REMOTE_URL}@${SHA}"
        tutor config save --set \
            "COURSE_INVENTORY_PIP_SPEC=course-inventory @ git+${REMOTE_URL}@${SHA}"
        ;;
    git)
        pip install tutor-contrib-course-inventory
        # Default COURSE_INVENTORY_PIP_SPEC pins to the matching version.
        ;;
    *)
        fail "PLUGIN_SOURCE must be 'local' or 'git' (got '${PLUGIN_SOURCE}')"
        ;;
esac

tutor plugins enable course-inventory
tutor config save

# ---- step 2: build + launch ------------------------------------------------

log "step 2/6 — building openedx image with course-inventory (slow)"
tutor images build openedx

log "step 3/6 — launching Tutor stack (slow)"
tutor local launch --non-interactive

# Migrations come for free via the plugin's CLI_DO_INIT_TASKS hook.

# ---- step 3: seed a staff user + a fake course -----------------------------

log "step 4/6 — seeding staff user and one course"

# Note the `cms` subcommand after `manage.py` — Open edX's manage.py
# is a router; bare `python manage.py shell` is rejected with
# "invalid choice: 'shell' (choose from 'lms', 'cms')".
#
# We do three things in one shell:
#   1. Create a staff superuser.
#   2. Seed a fake CourseOverview.
#   3. Pre-create a Django session for that user and print the key.
# Step 3 lets us skip Open edX's login UI entirely — /admin/login/
# 302s to /login (LMS), which 302s to an SSO chain, which curl can't
# usefully follow. With the session key in hand we just set the
# sessionid cookie directly and the auth middleware accepts the
# request. Same pattern Django's force_login uses in tests.
seed_output=$(tutor local run cms python manage.py cms shell -c "
from importlib import import_module
from django.conf import settings as dj_settings
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

User = get_user_model()
u, _ = User.objects.get_or_create(
    username='${STAFF_USER}',
    defaults={'email': '${STAFF_USER}@example.com'},
)
u.set_password('${STAFF_PASS}')
u.is_staff = True
u.is_superuser = True
u.save()
print('seeded staff user:', u.username)

key = CourseKey.from_string('${COURSE_KEY}')
co, _ = CourseOverview.objects.get_or_create(
    id=key,
    defaults={
        'display_name': '${COURSE_NAME}',
        'org': 'edX',
        'catalog_visibility': 'both',
        'self_paced': False,
        # CourseOverview.VERSION is the cache schema version
        # edx-platform uses internally. NOT NULL with no default.
        'version': CourseOverview.VERSION,
    },
)
print('seeded course:', co.id)

SessionStore = import_module(dj_settings.SESSION_ENGINE).SessionStore
session = SessionStore()
session['_auth_user_id'] = str(u.id)
session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
# Django 4.1+ AuthenticationMiddleware.get_user() requires the
# session-auth-hash for validation; without it, the session is
# flushed and the request is treated as anonymous. This is what
# auth.login() / force_login() set under the hood.
session['_auth_user_hash'] = u.get_session_auth_hash()
session.save()
print('SESSION_KEY:', session.session_key)
" 2>&1)

# Echo so the run log shows what we got.
printf '%s\n' "${seed_output}"

SESSION_KEY=$(printf '%s' "${seed_output}" \
              | grep -E '^SESSION_KEY:' \
              | awk '{print $2}' \
              | tr -d '\r' \
              || true)
[[ -n "${SESSION_KEY}" ]] || fail "could not extract SESSION_KEY from seed output"
log "  - pre-created session: ${SESSION_KEY:0:8}..."

# ---- step 4: hit the dashboard via curl + session cookie -------------------

log "step 5/6 — assertions"

# Tutor's `local launch` brings up Caddy on the host's :80 (HTTP only —
# HTTPS needs an ACME-able domain), and does NOT edit /etc/hosts. From
# inside the runner, `studio.local.openedx.io` won't resolve. Use
# --resolve to map it to 127.0.0.1 and stay on plain HTTP. The Host
# header still drives Caddy's routing to the CMS upstream.
CURL=(curl -s --resolve "${STUDIO_HOST}:80:127.0.0.1"
      -b "sessionid=${SESSION_KEY}")
BASE="http://${STUDIO_HOST}"

# Hit the inventory.
log "  - GET /course-inventory/ as ${STAFF_USER}"
body=$("${CURL[@]}" -w '\n__STATUS__=%{http_code}\n' "${BASE}/course-inventory/" || true)
status=$(printf '%s' "${body}" | sed -n 's/^__STATUS__=//p')
if [[ "${status}" != "200" ]]; then
    err "expected 200, got '${status}' on /course-inventory/"
    err "first 800 bytes of response:"
    printf '%s\n' "${body:0:800}"
    err "(end of dump)"
    "${CURL[@]}" -v "${BASE}/course-inventory/" 2>&1 | head -40 || true
    fail "abort"
fi
echo "${body}" | grep -q "${COURSE_NAME}" \
    || fail "expected display_name '${COURSE_NAME}' not in dashboard HTML"
echo "${body}" | grep -q "django_htmx/htmx.min.js" \
    || fail "expected same-origin HTMX script tag not present"
if echo "${body}" | grep -q "unpkg.com"; then
    fail "page references unpkg.com CDN (should be same-origin)"
fi
log "  - dashboard HTML looks right"

# Hit the export.
log "  - GET /course-inventory/export?format=csv"
csv=$("${CURL[@]}" "${BASE}/course-inventory/export?format=csv" || true)
echo "${csv}" | head -1 | grep -q "course_id,display_name" \
    || fail "CSV header row malformed"
echo "${csv}" | grep -q "${COURSE_KEY}" \
    || fail "seeded course_id not in CSV body"
log "  - CSV export looks right"

log "step 6/6 — smoke test passed"
