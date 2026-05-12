#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-$HOME/ezpaw}"
DB_USER="${EZPAW_DB_USER:-ezpaw}"
DB_NAME="${EZPAW_DB_NAME:-ezpaw}"
DB_PASSWORD="${EZPAW_DB_PASSWORD:-}"
DB_HOST="${EZPAW_DB_HOST:-localhost}"
DB_PORT="${EZPAW_DB_PORT:-5432}"
FLASK_PORT="${EZPAW_FLASK_PORT:-5000}"
SKIP_DB="${EZPAW_SKIP_DB:-0}"
SKIP_GPAW="${EZPAW_SKIP_GPAW:-0}"
INTERACTIVE="${EZPAW_INTERACTIVE:-1}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { printf "${CYAN}[INFO]${NC}  %s\n" "$*"; }
ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
error() { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; exit 1; }

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Install and configure ezpaw on a fresh machine.

Options:
  --skip-db          Skip PostgreSQL database creation and schema load
  --skip-gpaw        Skip GPAW pip install (for systems with GPAW already available)
  --non-interactive   Run without prompting (use env vars or defaults)
  --project DIR      Set project root directory (default: \$HOME/ezpaw)
  -h, --help         Show this help message

Environment variables (used in --non-interactive mode or to override defaults):
  PROJECT             Project root directory
  EZPAW_DB_USER       PostgreSQL user (default: ezpaw)
  EZPAW_DB_NAME       PostgreSQL database name (default: ezpaw)
  EZPAW_DB_PASSWORD   PostgreSQL password (prompted if not set)
  EZPAW_DB_HOST       PostgreSQL host (default: localhost)
  EZPAW_DB_PORT       PostgreSQL port (default: 5432)
  EZPAW_FLASK_PORT    Flask web UI port (default: 5000)
  EZPAW_SKIP_DB       Set to 1 to skip database setup
  EZPAW_SKIP_GPAW     Set to 1 to skip GPAW installation

For manual installation, see AGENTS.md in the project root.
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-db)       SKIP_DB=1; shift ;;
        --skip-gpaw)     SKIP_GPAW=1; shift ;;
        --non-interactive) INTERACTIVE=0; shift ;;
        --project)       PROJECT="$2"; shift 2 ;;
        -h|--help)       usage ;;
        *)               error "Unknown option: $1" ;;
    esac
done

info "ezpaw installer — project root: $PROJECT"

if [[ ! -d "$PROJECT" ]]; then
    error "Project directory $PROJECT does not exist. Clone or create it first."
fi

cd "$PROJECT"

if [[ "$INTERACTIVE" == "1" ]] && [[ -z "$DB_PASSWORD" ]]; then
    read -rsp "Enter PostgreSQL password for user '$DB_USER': " DB_PASSWORD
    echo
fi

if [[ -z "$DB_PASSWORD" ]]; then
    warn "No database password set — using empty password. Set EZPAW_DB_PASSWORD for unattended installs."
fi

# ── 1. System prerequisites ─────────────────────────────────────────────────

info "Installing system prerequisites..."
sudo apt update
sudo apt install -y python3.11-venv python3-pip postgresql libfftw3-dev libgsl-dev libxc-dev

# ── 2. Python virtual environment ───────────────────────────────────────────

info "Setting up Python virtual environment..."
if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
    ok "Virtual environment created at .venv/"
else
    ok "Virtual environment already exists at .venv/"
fi

source .venv/bin/activate

# ── 3. Install ezpaw package ────────────────────────────────────────────────

info "Installing ezpaw package..."
pip install -e .

# ── 4. Database setup ───────────────────────────────────────────────────────

if [[ "$SKIP_DB" == "1" ]]; then
    warn "Skipping database setup (--skip-db)"
else
    info "Setting up PostgreSQL database..."
    sudo systemctl start postgresql

    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
        ok "PostgreSQL user '$DB_USER' already exists"
    else
        sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
        ok "Created PostgreSQL user '$DB_USER'"
    fi

    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        ok "PostgreSQL database '$DB_NAME' already exists"
    else
        sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
        ok "Created PostgreSQL database '$DB_NAME'"
    fi

    info "Loading database schema..."
    DB_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    psql "$DB_URL" < ezpaw/schema.sql
    ok "Database schema loaded"

    info "Writing .env file..."
    cat > .env <<ENVEOF
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}
DB_PASSWORD=${DB_PASSWORD}
ENVEOF
    chmod 600 .env
    ok ".env written (mode 600)"
fi

# ── 5. Configuration ────────────────────────────────────────────────────────

info "Setting up configuration..."
if [[ ! -f config.yaml ]]; then
    cp config.yaml.example config.yaml
    ok "Created config.yaml from config.yaml.example"
else
    ok "config.yaml already exists — leaving it as-is"
fi

# ── 6. GPAW (optional) ──────────────────────────────────────────────────────

if [[ "$SKIP_GPAW" == "1" ]]; then
    warn "Skipping GPAW installation (--skip-gpaw)"
else
    info "Installing GPAW and ASE..."
    pip install ase
    pip install --no-build-isolation gpaw
    ok "GPAW installed"
fi

# ── 7. Shell environment ────────────────────────────────────────────────────

info "Configuring shell environment..."
BASHRC_MARKER="# ezpaw — required for this project"

if grep -qF "$BASHRC_MARKER" ~/.bashrc 2>/dev/null; then
    ok "~/.bashrc already has ezpaw environment block"
else
    cat >> ~/.bashrc <<BASHEOF

$BASHRC_MARKER
export PROJECT="$PROJECT"
export PATH="\$PROJECT/.venv/bin:\$PATH"
export LD_LIBRARY_PATH="\$PROJECT/.venv/lib:\$LD_LIBRARY_PATH"
BASHEOF
    ok "Added ezpaw environment block to ~/.bashrc"
fi

# ── 8. Systemd service ──────────────────────────────────────────────────────

info "Installing Flask systemd user service..."
mkdir -p ~/.config/systemd/user
cp systemd/ezpaw-flask.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable ezpaw-flask
ok "ezpaw-flask service installed and enabled"

# ── 9. Output directories ───────────────────────────────────────────────────

mkdir -p logs output
ok "Created logs/ and output/ directories"

# ── Done ────────────────────────────────────────────────────────────────────

echo ""
ok "ezpaw installation complete!"
echo ""
info "Next steps:"
echo "  1. Edit config.yaml if needed (database credentials, Flask port, etc.)"
echo "  2. Run:  source ~/.bashrc"
echo "  3. Start the web UI:  ezpaw web"
echo "  4. Or run a calculation:  ezpaw run your_script.py"
echo ""
info "For manual setup or troubleshooting, see AGENTS.md"