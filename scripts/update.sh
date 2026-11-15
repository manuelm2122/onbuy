#!/usr/bin/env bash
# Actualiza OnBuySolutions en el VPS: GitHub -> dependencias -> build -> reinicio.
# Uso: sudo bash /var/www/auditoria/scripts/update.sh
# Variables opcionales: APP_DIR, BRANCH, BACKEND_SERVICE, HEALTH_URL, SKIP_FRONTEND=1
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/var/www/auditoria}"
BACKEND_SERVICE="${BACKEND_SERVICE:-}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8001/api/}"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/auditoria}"

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m[aviso] %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m[error] %s\033[0m\n' "$*" >&2; exit 1; }
trap 'die "Falló en la línea $LINENO. No se reinició nada después de este punto."' ERR

find_venv() {
  local d
  for d in "$APP_DIR/backend/venv" "$APP_DIR/backend/.venv" "$APP_DIR/venv" "$APP_DIR/.venv"; do
    [ -x "$d/bin/pip" ] && { echo "$d"; return; }
  done
  python3 -m venv "$APP_DIR/backend/venv"
  echo "$APP_DIR/backend/venv"
}

restart_backend() {
  local svc="$BACKEND_SERVICE"
  if [ -z "$svc" ] && command -v systemctl >/dev/null; then
    svc="$(grep -rl "$APP_DIR" /etc/systemd/system/*.service 2>/dev/null | head -n1 | xargs -r basename || true)"
  fi
  if [ -n "$svc" ] && command -v systemctl >/dev/null && systemctl cat "$svc" >/dev/null 2>&1; then
    systemctl restart "$svc"
    echo "systemd: $svc reiniciado"
    return
  fi
  if command -v pm2 >/dev/null && pm2 jlist 2>/dev/null | grep -q "$APP_DIR"; then
    pm2 jlist | python3 -c "
import sys, json
for p in json.load(sys.stdin):
    if '$APP_DIR' in (p.get('pm2_env', {}).get('pm_cwd') or ''):
        print(p['name'])" | sort -u | xargs -r -n1 pm2 restart --update-env
    return
  fi
  if command -v supervisorctl >/dev/null && grep -rqs "$APP_DIR" /etc/supervisor/conf.d/ 2>/dev/null; then
    grep -rls "$APP_DIR" /etc/supervisor/conf.d/ | xargs -r grep -hoP '^\[program:\K[^\]]+' | sort -u | xargs -r -n1 supervisorctl restart
    return
  fi
  die "No encontré cómo se ejecuta el backend. Vuelve a correr indicando el servicio: BACKEND_SERVICE=nombre.service"
}

main() {
  [ -d "$APP_DIR/.git" ] || die "$APP_DIR no es un repositorio git"
  cd "$APP_DIR"
  git config --global --add safe.directory "$APP_DIR" 2>/dev/null || true
  local branch="${BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"
  local before; before="$(git rev-parse HEAD)"

  step "1/6 Copia de seguridad de archivos subidos y .env"
  mkdir -p "$BACKUP_DIR"
  local keep; keep="$(mktemp -d)"
  if [ -d backend/uploads ]; then
    cp -a backend/uploads "$keep/uploads"
    tar -czf "$BACKUP_DIR/uploads_$STAMP.tar.gz" -C backend uploads
  fi
  for f in backend/.env frontend/.env; do
    [ -f "$f" ] && cp -a "$f" "$BACKUP_DIR/$(dirname "$f")_env_$STAMP"
  done
  ls -1t "$BACKUP_DIR"/uploads_*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm -f
  echo "Respaldo en $BACKUP_DIR"

  step "2/6 Sincronizando con GitHub (rama $branch)"
  git fetch origin "$branch"
  git checkout -- backend/uploads 2>/dev/null || true
  if ! git merge --ff-only "origin/$branch"; then
    [ -d "$keep/uploads" ] && rsync -a --delete "$keep/uploads/" backend/uploads/
    die "Hay cambios locales en el VPS que chocan con GitHub. Revisa 'git status' en $APP_DIR; no se modificó el código."
  fi
  if [ -d "$keep/uploads" ]; then
    mkdir -p backend/uploads
    rsync -a --delete "$keep/uploads/" backend/uploads/
  fi
  rm -rf "$keep"
  local after; after="$(git rev-parse HEAD)"
  echo "Código: ${before:0:7} -> ${after:0:7}"
  [ -f backend/.env ] || die "Falta backend/.env"
  if [ "${SKIP_FRONTEND:-0}" != "1" ] && [ -z "${REACT_APP_BACKEND_URL:-}" ] \
     && ! grep -qs '^REACT_APP_BACKEND_URL=' frontend/.env frontend/.env.production frontend/.env.local frontend/.env.production.local; then
    die "No encuentro REACT_APP_BACKEND_URL (ni en frontend/.env* ni como variable). Crea frontend/.env con: REACT_APP_BACKEND_URL=https://tu-dominio"
  fi

  step "3/6 Dependencias del backend"
  local venv; venv="$(find_venv)"
  "$venv/bin/pip" install -q --upgrade pip
  "$venv/bin/pip" install -q -r backend/requirements.txt
  "$venv/bin/pip" install -q emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ \
    || warn "No se pudo instalar emergentintegrations: la opción 'Universal Key de Emergent' no funcionará (Gemini y Vertex sí)."
  PYTHONDONTWRITEBYTECODE=1 "$venv/bin/python" -c "import sys; sys.path.insert(0, 'backend'); import server" \
    || die "El backend no arranca con el código nuevo. No se reinició el servicio; la web sigue con la versión anterior en memoria."

  if [ "${SKIP_FRONTEND:-0}" != "1" ]; then
    step "4/6 Compilando el frontend"
    command -v yarn >/dev/null || die "Falta yarn. Instálalo con: npm install -g yarn"
    (
      cd frontend
      yarn install --frozen-lockfile --silent
      rm -rf build_new
      BUILD_PATH=build_new CI=false GENERATE_SOURCEMAP=false yarn build
      [ -f build_new/index.html ] || exit 1
      rm -rf build_old
      [ -d build ] && mv build build_old
      mv build_new build
      rm -rf build_old
    )
  else
    step "4/6 Frontend omitido (SKIP_FRONTEND=1)"
  fi

  step "5/6 Reiniciando el backend"
  local owner; owner="$(stat -c '%U:%G' "$APP_DIR")"
  chown -R "$owner" backend/uploads frontend/build 2>/dev/null || true
  restart_backend
  if command -v nginx >/dev/null && nginx -t >/dev/null 2>&1; then
    systemctl reload nginx 2>/dev/null || true
  fi

  step "6/6 Verificando"
  local i ok=0
  for i in $(seq 1 15); do
    if curl -fsS -m 5 "$HEALTH_URL" >/dev/null 2>&1; then ok=1; break; fi
    sleep 2
  done
  if [ "$ok" = 1 ]; then
    echo "Backend respondiendo en $HEALTH_URL"
  else
    warn "El backend no respondió en $HEALTH_URL. Si usa otro puerto, define HEALTH_URL; si no, revisa los logs del servicio."
  fi
  echo "Versión anterior: $before"
  printf '\n\033[1;32mActualización terminada (%s).\033[0m\n' "${after:0:7}"
}

main "$@"
