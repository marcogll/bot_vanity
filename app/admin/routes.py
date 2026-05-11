import csv
import html
import io
import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, quote, urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.catalog_sync import sync_service_catalog_from_docs, sync_service_catalog_from_fresha_csv
from app.database import AsyncSessionLocal, get_db_session
from app.janitor import purge_expired_records
from app.knowledge_engine import get_knowledge_engine
from app.models import (
    AdminAuditLog,
    AdminUser,
    CitaCompletada,
    CitaPendiente,
    Interaccion,
    ServiceCatalog,
    SesionMemoria,
    WebhookEvent,
)
from app.security import (
    generate_csrf_token,
    hash_password,
    issue_admin_session_token,
    read_admin_session_token,
    verify_password,
)


admin_router = APIRouter(prefix="/admin", tags=["admin"])

DB_TABLES: dict[str, tuple[Any, list[str], str]] = {
    "interacciones": (
        Interaccion,
        ["id", "whatsapp_id", "role", "content", "timestamp"],
        "timestamp",
    ),
    "sesiones_memoria": (
        SesionMemoria,
        [
            "id",
            "whatsapp_id",
            "push_name",
            "resumen_perfil",
            "servicio_interes",
            "ultima_cotizacion",
            "score_conversion",
            "updated_at",
        ],
        "updated_at",
    ),
    "citas_pendientes": (
        CitaPendiente,
        [
            "id",
            "whatsapp_id",
            "push_name",
            "servicio_interes",
            "booking_status",
            "deposit_status",
            "appointment_proof_message",
            "updated_at",
        ],
        "updated_at",
    ),
    "citas_completadas": (
        CitaCompletada,
        [
            "id",
            "whatsapp_id",
            "push_name",
            "servicio_interes",
            "booking_status",
            "deposit_status",
            "appointment_date",
            "start_time",
            "total_amount",
            "completed_at",
        ],
        "completed_at",
    ),
    "webhook_events": (
        WebhookEvent,
        ["id", "event_kind", "whatsapp_id", "instance_name", "event_key", "created_at"],
        "created_at",
    ),
    "service_catalog": (
        ServiceCatalog,
        [
            "id",
            "external_service_id",
            "name",
            "base_price",
            "purchase_price",
            "duration_minutes",
            "additional_time_minutes",
            "tax_percent",
            "description",
            "category",
            "service_type",
            "is_active",
            "updated_at",
        ],
        "updated_at",
    ),
}


@admin_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    settings = get_settings()
    if not settings.admin_webui_enabled:
        return HTMLResponse("Admin web UI disabled", status_code=503)
    body = """
    <section class="panel narrow">
      <h1>Acceso Administrativo</h1>
      <p class="muted">Panel interno de control para Sofía.</p>
      <form method="post" action="/admin/login" class="stack">
        <label>Usuario<input type="text" name="username" autocomplete="username" required></label>
        <label>Password<input type="password" name="password" autocomplete="current-password" required></label>
        <button type="submit">Entrar</button>
      </form>
    </section>
    """
    return HTMLResponse(_render_page("Login", body, request, current_user=None))


@admin_router.post("/login")
async def login_submit(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    settings = get_settings()
    if not settings.admin_webui_enabled:
        return HTMLResponse("Admin web UI disabled", status_code=503)
    form = await _parse_form(request)
    username = form.get("username", "").strip()
    password = form.get("password", "")
    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        return _redirect("/admin/login", "Credenciales inválidas.")
    now = datetime.now(UTC)
    if user.locked_until and user.locked_until > now:
        return _redirect("/admin/login", "Usuario bloqueado temporalmente por intentos fallidos.")
    if not user.is_active or not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.admin_login_max_attempts:
            user.locked_until = now + timedelta(minutes=settings.admin_lockout_minutes)
            user.failed_login_attempts = 0
        await db.commit()
        return _redirect("/admin/login", "Credenciales inválidas.")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    await _audit(
        db,
        request,
        user,
        action="admin.login",
        entity_type="admin_user",
        entity_id=str(user.id),
    )
    await db.commit()
    csrf_token = generate_csrf_token()
    token = issue_admin_session_token(
        user_id=str(user.id),
        csrf_token=csrf_token,
        expires_minutes=settings.admin_session_minutes,
    )
    destination = "/admin/password" if user.must_rotate_password else "/admin"
    response = RedirectResponse(destination, status_code=303)
    _set_session_cookie(response, token)
    return response


@admin_router.post("/logout")
async def logout_submit(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, _ = await _require_admin(request, db, allow_password_rotation=True)
    if isinstance(current_user, Response):
        return current_user
    await _audit(db, request, current_user, action="admin.logout")
    await db.commit()
    response = RedirectResponse("/admin/login", status_code=303)
    _clear_session_cookie(response)
    return response


@admin_router.get("/password", response_class=HTMLResponse)
async def password_page(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, session_payload = await _require_admin(request, db, allow_password_rotation=True)
    if isinstance(current_user, Response):
        return current_user
    body = f"""
    <section class="panel narrow">
      <h1>Rotación de Password</h1>
      <p class="muted">La cuenta usa un password temporal. Define uno fuerte para continuar.</p>
      <form method="post" action="/admin/password" class="stack">
        {_csrf_input(session_payload)}
        <label>Nuevo password<input type="password" name="password" autocomplete="new-password" required></label>
        <label>Confirmar password<input type="password" name="password_confirm" autocomplete="new-password" required></label>
        <button type="submit">Guardar password</button>
      </form>
    </section>
    """
    return HTMLResponse(_render_page("Rotar Password", body, request, current_user=current_user))


@admin_router.post("/password")
async def password_submit(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, session_payload = await _require_admin(request, db, allow_password_rotation=True)
    if isinstance(current_user, Response):
        return current_user
    form = await _parse_form(request)
    if not _valid_csrf(form, session_payload):
        return HTMLResponse("CSRF inválido", status_code=400)
    password = form.get("password", "")
    confirmation = form.get("password_confirm", "")
    error = _validate_password_strength(password, confirmation)
    if error:
        return _redirect("/admin/password", error)
    current_user.password_hash = hash_password(password)
    current_user.password_algo = "scrypt"
    current_user.temporary_password = False
    current_user.must_rotate_password = False
    current_user.password_expires_at = None
    await _audit(db, request, current_user, action="admin.password.rotate")
    await db.commit()
    return _redirect("/admin", "Password actualizado correctamente.")


@admin_router.get("", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, _ = await _require_admin(request, db)
    if isinstance(current_user, Response):
        return current_user
    conversation_count = await _scalar_count(db, select(func.count(SesionMemoria.id)))
    pending_count = await _scalar_count(db, select(func.count(CitaPendiente.id)))
    completed_count = await _scalar_count(db, select(func.count(CitaCompletada.id)))
    interaction_count = await _scalar_count(db, select(func.count(Interaccion.id)))
    service_count = await _scalar_count(db, select(func.count(ServiceCatalog.id)))
    runtime = _runtime_state(request)
    db_ok = await _db_health(db)
    evolution_configured = bool(get_settings().evolution_api_url.strip() and get_settings().evolution_api_key.strip())
    recent_audit = await db.execute(select(AdminAuditLog).order_by(desc(AdminAuditLog.created_at)).limit(10))
    recent_items = recent_audit.scalars().all()
    cards = "".join(
        _metric_card(label, value)
        for label, value in (
            ("Sesiones CRM", conversation_count),
            ("Citas pendientes", pending_count),
            ("Citas completadas", completed_count),
            ("Interacciones", interaction_count),
            ("Servicios", service_count),
        )
    )
    audit_rows = "".join(
        f"<tr><td>{_format_datetime(item.created_at)}</td><td>{_e(item.action)}</td><td>{_e(item.entity_type or '-')}</td><td>{_e(item.entity_id or '-')}</td></tr>"
        for item in recent_items
    ) or "<tr><td colspan='4' class='muted'>Sin eventos aún.</td></tr>"
    body = f"""
    <section class="grid cards">{cards}</section>
    <section class="grid two">
      <article class="panel">
        <h2>Estado del Sistema</h2>
        <ul class="kv">
          <li><strong>DB</strong><span>{'OK' if db_ok else 'Error'}</span></li>
          <li><strong>Evolution</strong><span>{'Configurado' if evolution_configured else 'Sin configurar'}</span></li>
          <li><strong>Bot global</strong><span>{'Pausado' if runtime['bot_paused'] else 'Activo'}</span></li>
          <li><strong>Follow-ups</strong><span>{'Pausados' if runtime['followups_paused'] else 'Activos'}</span></li>
          <li><strong>Último janitor</strong><span>{_format_datetime(runtime.get('last_janitor_run_at'))}</span></li>
          <li><strong>Último reset runtime</strong><span>{_format_datetime(runtime.get('last_runtime_reset_at'))}</span></li>
        </ul>
      </article>
      <article class="panel">
        <h2>Acciones Rápidas</h2>
        <div class="actions">
          {_action_form('/admin/actions/pause-bot', 'Pausar Bot', _csrf_input(_session_payload_from_request(request)))}
          {_action_form('/admin/actions/resume-bot', 'Reanudar Bot', _csrf_input(_session_payload_from_request(request)))}
          {_action_form('/admin/actions/clear-runtime', 'Limpiar Runtime', _csrf_input(_session_payload_from_request(request)))}
          {_action_form('/admin/actions/run-janitor', 'Ejecutar Janitor', _csrf_input(_session_payload_from_request(request)))}
          {_action_form('/admin/actions/sync-service-catalog', 'Sincronizar Servicios desde Docs', _csrf_input(_session_payload_from_request(request)))}
          {_action_form('/admin/actions/sync-fresha-catalog', 'Sincronizar Servicios desde Fresha CSV', _csrf_input(_session_payload_from_request(request)))}
          {_action_form('/admin/actions/reload-docs', 'Recargar Docs', _csrf_input(_session_payload_from_request(request)))}
        </div>
      </article>
    </section>
    <section class="panel">
      <h2>Auditoría Reciente</h2>
      <table>
        <thead><tr><th>Fecha</th><th>Acción</th><th>Entidad</th><th>ID</th></tr></thead>
        <tbody>{audit_rows}</tbody>
      </table>
    </section>
    """
    return HTMLResponse(_render_page("Dashboard", body, request, current_user=current_user))


@admin_router.get("/services", response_class=HTMLResponse)
async def services_page(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, session_payload = await _require_admin(request, db)
    if isinstance(current_user, Response):
        return current_user
    result = await db.execute(select(ServiceCatalog).order_by(ServiceCatalog.category, ServiceCatalog.name))
    all_services = result.scalars().all()
    current_q = request.query_params.get("q", "").strip()
    current_category = request.query_params.get("category", "").strip()
    current_service_type = request.query_params.get("service_type", "").strip()
    services = [
        item
        for item in all_services
        if _service_matches_filters(
            item,
            query=current_q,
            category=current_category,
            service_type=current_service_type,
        )
    ]
    categories = sorted({item.category for item in all_services if item.category})
    service_return_to = _services_return_to(request)
    service_rows = "".join(
        _service_row_html(item, session_payload, service_return_to)
        for item in services
    ) or "<tr><td colspan='13' class='muted'>No hay servicios cargados.</td></tr>"
    filters_html = f"""
      <form method="get" action="/admin/services" class="toolbar wrap filters">
        <input type="search" name="q" value="{_e(current_q)}" placeholder="Buscar por nombre, descripción, ID o categoría">
        <select name="category">
          <option value="">Todas las categorías</option>
          {_service_category_options(categories, current_category)}
        </select>
        <select name="service_type">
          <option value="">Todos los tipos</option>
          {_service_type_options(current_service_type, allow_blank=False)}
        </select>
        <button type="submit">Filtrar</button>
        <a class="button secondary" href="/admin/services">Limpiar</a>
      </form>
      <p class="muted">Mostrando {len(services)} de {len(all_services)} servicios.</p>
    """
    body = f"""
    <section class="grid two">
      <article class="panel">
        <h1>Servicios</h1>
        {filters_html}
        <div class="table-wrap">
        <table class="wide-table">
          <thead><tr><th>ID del servicio</th><th>ID externo</th><th>Nombre del servicio</th><th>Precio de venta</th><th>Duración</th><th>Precio de compra</th><th>Tiempo adicional</th><th>Impuestos</th><th>Descripción</th><th>Nombre de la categoría</th><th>Tipo de servicio</th><th>Activo</th><th>Acciones</th></tr></thead>
          <tbody>{service_rows}</tbody>
        </table>
        </div>
        <div class="toolbar">
          <a class="button secondary" href="/admin/services/export.csv">Exportar CSV</a>
          <a class="button secondary" href="/admin/services/export.json">Exportar JSON</a>
        </div>
      </article>
      <article class="panel">
        <h2>Nuevo servicio</h2>
        <form method="post" action="/admin/services" class="stack">
          {_csrf_input(session_payload)}
          <input type="hidden" name="return_to" value="{_e(service_return_to)}">
          <label>Nombre<input type="text" name="name" value="" required></label>
          <label>ID externo<input type="text" name="external_service_id" value="" placeholder="Opcional"></label>
          <label>Slug<input type="text" name="slug" value="" placeholder="se-autogenera-si-vacio"></label>
          <label>Nombre de la categoría<input type="text" name="category" value="{_e(current_category or 'General')}" required></label>
          <label>Tipo de servicio
            <select name="service_type">
              {_service_type_options(current_service_type or 'service')}
            </select>
          </label>
          <label>Descripción<textarea name="description" rows="4"></textarea></label>
          <label>Precio de venta<input type="number" name="base_price" value="0" step="0.01" min="0" required></label>
          <label>Precio de compra<input type="number" name="purchase_price" value="0" step="0.01" min="0" required></label>
          <label>Duración (minutos)<input type="number" name="duration_minutes" value="0" min="0" required></label>
          <label>Tiempo adicional (minutos)<input type="number" name="additional_time_minutes" value="0" min="0" required></label>
          <label>Impuestos %<input type="number" name="tax_percent" value="0" step="0.01" min="0" required></label>
          <label class="check"><input type="checkbox" name="is_active" checked> Servicio activo</label>
          <button type="submit">Crear servicio</button>
        </form>
      </article>
    </section>
    <section class="panel">
      <h2>Importar catálogo</h2>
      <form method="post" action="/admin/services/import" class="stack">
        {_csrf_input(session_payload)}
        <input type="hidden" name="return_to" value="{_e(service_return_to)}">
        <label>Formato
          <select name="format">
            <option value="csv">CSV</option>
            <option value="json">JSON</option>
          </select>
        </label>
        <label>Pega aquí el contenido del archivo<textarea name="payload_text" rows="12" placeholder='[{{
  "name": "Gelish",
  "category": "Uñas",
  "service_type": "service",
  "base_price": 450,
  "purchase_price": 0,
  "duration_minutes": 60,
  "additional_time_minutes": 0,
  "tax_percent": 0
}}]'></textarea></label>
        <button type="submit">Importar</button>
      </form>
    </section>
    """
    return HTMLResponse(_render_page("Servicios", body, request, current_user=current_user))


@admin_router.post("/services")
async def create_service(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, session_payload = await _require_admin(request, db)
    if isinstance(current_user, Response):
        return current_user
    form = await _parse_form(request)
    return_to = _safe_return_to(form.get("return_to", ""))
    if not _valid_csrf(form, session_payload):
        return HTMLResponse("CSRF inválido", status_code=400)
    error, payload = _parse_service_payload(form)
    if error:
        return _redirect(return_to, error)
    existing = await db.execute(select(ServiceCatalog).where(ServiceCatalog.slug == payload["slug"]))
    if existing.scalar_one_or_none():
        return _redirect(return_to, "Ya existe un servicio con ese slug.")
    service = ServiceCatalog(**payload)
    db.add(service)
    await _audit(db, request, current_user, action="service.create", entity_type="service_catalog", payload=payload)
    await db.commit()
    return _redirect(return_to, "Servicio creado.")


@admin_router.post("/services/{service_id}")
async def update_service(service_id: str, request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, session_payload = await _require_admin(request, db)
    if isinstance(current_user, Response):
        return current_user
    form = await _parse_form(request)
    return_to = _safe_return_to(form.get("return_to", ""))
    if not _valid_csrf(form, session_payload):
        return HTMLResponse("CSRF inválido", status_code=400)
    try:
        service_uuid = uuid.UUID(service_id)
    except ValueError:
        return _redirect(return_to, "ID de servicio inválido.")
    result = await db.execute(select(ServiceCatalog).where(ServiceCatalog.id == service_uuid))
    service = result.scalar_one_or_none()
    if service is None:
        return _redirect(return_to, "Servicio no encontrado.")
    error, payload = _parse_service_payload(form)
    if error:
        return _redirect(return_to, error)
    duplicate = await db.execute(select(ServiceCatalog).where(ServiceCatalog.slug == payload["slug"], ServiceCatalog.id != service.id))
    if duplicate.scalar_one_or_none():
        return _redirect(return_to, "Ese slug ya está en uso.")
    for key, value in payload.items():
        setattr(service, key, value)
    await _audit(
        db,
        request,
        current_user,
        action="service.update",
        entity_type="service_catalog",
        entity_id=str(service.id),
        payload=payload,
    )
    await db.commit()
    return _redirect(return_to, "Servicio actualizado.")


@admin_router.post("/services/{service_id}/delete")
async def delete_service(service_id: str, request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, session_payload = await _require_admin(request, db)
    if isinstance(current_user, Response):
        return current_user
    form = await _parse_form(request)
    return_to = _safe_return_to(form.get("return_to", ""))
    if not _valid_csrf(form, session_payload):
        return HTMLResponse("CSRF inválido", status_code=400)
    try:
        service_uuid = uuid.UUID(service_id)
    except ValueError:
        return _redirect(return_to, "ID de servicio inválido.")
    result = await db.execute(select(ServiceCatalog).where(ServiceCatalog.id == service_uuid))
    service = result.scalar_one_or_none()
    if service is None:
        return _redirect(return_to, "Servicio no encontrado.")
    await db.delete(service)
    await _audit(
        db,
        request,
        current_user,
        action="service.delete",
        entity_type="service_catalog",
        entity_id=service_id,
    )
    await db.commit()
    return _redirect(return_to, "Servicio eliminado.")


@admin_router.post("/services/import")
async def import_services(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, session_payload = await _require_admin(request, db)
    if isinstance(current_user, Response):
        return current_user
    form = await _parse_form(request)
    return_to = _safe_return_to(form.get("return_to", ""))
    if not _valid_csrf(form, session_payload):
        return HTMLResponse("CSRF inválido", status_code=400)
    format_name = form.get("format", "csv").strip().lower()
    payload_text = form.get("payload_text", "")
    try:
        rows = _parse_import_rows(format_name, payload_text)
    except ValueError as exc:
        return _redirect(return_to, f"Importación inválida: {exc}")
    created = 0
    updated = 0
    for row in rows:
        error, payload = _parse_service_payload(row, import_mode=True)
        if error:
            continue
        result = await db.execute(select(ServiceCatalog).where(ServiceCatalog.slug == payload["slug"]))
        service = result.scalar_one_or_none()
        if service is None:
            db.add(ServiceCatalog(**payload, source=f"import:{format_name}"))
            created += 1
            continue
        for key, value in payload.items():
            setattr(service, key, value)
        service.source = f"import:{format_name}"
        updated += 1
    await _audit(
        db,
        request,
        current_user,
        action="service.import",
        entity_type="service_catalog",
        payload={"format": format_name, "created": created, "updated": updated},
    )
    await db.commit()
    return _redirect(return_to, f"Importación completada. Creados: {created}. Actualizados: {updated}.")


@admin_router.get("/services/export.csv")
async def export_services_csv(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, _ = await _require_admin(request, db)
    if isinstance(current_user, Response):
        return current_user
    result = await db.execute(select(ServiceCatalog).order_by(ServiceCatalog.category, ServiceCatalog.name))
    services = result.scalars().all()
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "id",
            "external_service_id",
            "slug",
            "name",
            "category",
            "service_type",
            "description",
            "base_price",
            "purchase_price",
            "duration_minutes",
            "additional_time_minutes",
            "tax_percent",
            "is_active",
            "source",
        ],
    )
    writer.writeheader()
    for item in services:
        writer.writerow(
            {
                "slug": item.slug,
                "id": str(item.id),
                "external_service_id": item.external_service_id or "",
                "name": item.name,
                "category": item.category,
                "service_type": item.service_type,
                "description": item.description or "",
                "base_price": item.base_price,
                "purchase_price": item.purchase_price,
                "duration_minutes": item.duration_minutes,
                "additional_time_minutes": item.additional_time_minutes,
                "tax_percent": item.tax_percent,
                "is_active": item.is_active,
                "source": item.source,
            }
        )
    return PlainTextResponse(
        buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="service_catalog.csv"'},
    )


@admin_router.get("/services/export.json")
async def export_services_json(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, _ = await _require_admin(request, db)
    if isinstance(current_user, Response):
        return current_user
    result = await db.execute(select(ServiceCatalog).order_by(ServiceCatalog.category, ServiceCatalog.name))
    services = result.scalars().all()
    payload = [
        {
            "id": str(item.id),
            "slug": item.slug,
            "name": item.name,
            "category": item.category,
            "service_type": item.service_type,
            "external_service_id": item.external_service_id,
            "description": item.description,
            "base_price": item.base_price,
            "purchase_price": item.purchase_price,
            "duration_minutes": item.duration_minutes,
            "additional_time_minutes": item.additional_time_minutes,
            "tax_percent": item.tax_percent,
            "is_active": item.is_active,
            "source": item.source,
        }
        for item in services
    ]
    return Response(
        json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="service_catalog.json"'},
    )


@admin_router.get("/crm", response_class=HTMLResponse)
async def crm_page(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, _ = await _require_admin(request, db)
    if isinstance(current_user, Response):
        return current_user
    search = request.query_params.get("q", "").strip().casefold()
    result = await db.execute(select(SesionMemoria).order_by(desc(SesionMemoria.updated_at)).limit(100))
    sessions = result.scalars().all()
    rows: list[str] = []
    for item in sessions:
        if search and search not in (item.whatsapp_id.casefold(), (item.push_name or "").casefold(), (item.resumen_perfil or "").casefold()):
            combined = " ".join([item.whatsapp_id, item.push_name or "", item.resumen_perfil or ""]).casefold()
            if search not in combined:
                continue
        rows.append(
            f"""
            <tr>
              <td><a href="/admin/crm/detail?whatsapp_id={quote(item.whatsapp_id)}">{_e(item.push_name or '-')}</a></td>
              <td>{_e(item.whatsapp_id)}</td>
              <td>{_e(item.servicio_interes or '-')}</td>
              <td>{_e(_truncate(item.resumen_perfil or '-', 120))}</td>
              <td>{_format_datetime(item.updated_at)}</td>
            </tr>
            """
        )
    body = f"""
    <section class="panel">
      <h1>CRM Crudo</h1>
      <form method="get" action="/admin/crm" class="toolbar">
        <input type="search" name="q" value="{_e(request.query_params.get('q', ''))}" placeholder="Buscar por nombre, número o resumen">
        <button type="submit">Buscar</button>
      </form>
      <table>
        <thead><tr><th>Nombre</th><th>WhatsApp</th><th>Servicio</th><th>Resumen</th><th>Actualizado</th></tr></thead>
        <tbody>{''.join(rows) or "<tr><td colspan='5' class='muted'>Sin resultados.</td></tr>"}</tbody>
      </table>
    </section>
    """
    return HTMLResponse(_render_page("CRM", body, request, current_user=current_user))


@admin_router.get("/crm/detail", response_class=HTMLResponse)
async def crm_detail(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, session_payload = await _require_admin(request, db)
    if isinstance(current_user, Response):
        return current_user
    whatsapp_id = request.query_params.get("whatsapp_id", "").strip()
    if not whatsapp_id:
        return _redirect("/admin/crm", "Falta whatsapp_id.")
    memory = (await db.execute(select(SesionMemoria).where(SesionMemoria.whatsapp_id == whatsapp_id))).scalar_one_or_none()
    pending = (await db.execute(select(CitaPendiente).where(CitaPendiente.whatsapp_id == whatsapp_id))).scalar_one_or_none()
    completed = (
        await db.execute(select(CitaCompletada).where(CitaCompletada.whatsapp_id == whatsapp_id).order_by(desc(CitaCompletada.completed_at)).limit(5))
    ).scalars().all()
    history = (
        await db.execute(select(Interaccion).where(Interaccion.whatsapp_id == whatsapp_id).order_by(desc(Interaccion.timestamp)).limit(50))
    ).scalars().all()
    history_rows = "".join(
        f"<tr><td>{_format_datetime(item.timestamp)}</td><td>{_e(item.role.value)}</td><td>{_e(_safe_content(item))}</td></tr>"
        for item in history
    ) or "<tr><td colspan='3' class='muted'>Sin historial.</td></tr>"
    completed_rows = "".join(
        f"<li>{_format_datetime(item.completed_at)} | {_e(item.servicio_interes or '-')} | {_e(item.deposit_status or '-')} | {_e(str(item.total_amount) if item.total_amount is not None else '-')}</li>"
        for item in completed
    ) or "<li class='muted'>Sin citas completadas.</li>"
    body = f"""
    <section class="grid two">
      <article class="panel">
        <h1>Contacto</h1>
        <ul class="kv">
          <li><strong>WhatsApp</strong><span>{_e(whatsapp_id)}</span></li>
          <li><strong>Nombre</strong><span>{_e(memory.push_name if memory else '-')}</span></li>
          <li><strong>Servicio interés</strong><span>{_e(memory.servicio_interes if memory else '-')}</span></li>
          <li><strong>Resumen</strong><span>{_e(memory.resumen_perfil if memory else '-')}</span></li>
          <li><strong>Última actualización</strong><span>{_format_datetime(memory.updated_at if memory else None)}</span></li>
        </ul>
        <form method="post" action="/admin/actions/clear-memory" class="stack compact">
          {_csrf_input(session_payload)}
          <input type="hidden" name="whatsapp_id" value="{_e(whatsapp_id)}">
          <button type="submit" class="danger">Borrar memoria y chat</button>
        </form>
      </article>
      <article class="panel">
        <h2>Cita pendiente</h2>
        <ul class="kv">
          <li><strong>Estado booking</strong><span>{_e(pending.booking_status if pending else '-')}</span></li>
          <li><strong>Estado depósito</strong><span>{_e(pending.deposit_status if pending else '-')}</span></li>
          <li><strong>Servicio</strong><span>{_e(pending.servicio_interes if pending else '-')}</span></li>
          <li><strong>Comprobante</strong><span>{_e(pending.appointment_proof_message if pending else '-')}</span></li>
        </ul>
        <h2>Citas completadas</h2>
        <ul>{completed_rows}</ul>
      </article>
    </section>
    <section class="panel">
      <h2>Historial reciente</h2>
      <table>
        <thead><tr><th>Fecha</th><th>Rol</th><th>Contenido</th></tr></thead>
        <tbody>{history_rows}</tbody>
      </table>
    </section>
    """
    return HTMLResponse(_render_page("CRM Detail", body, request, current_user=current_user))


@admin_router.get("/db/{table_name}", response_class=HTMLResponse)
async def db_table_view(table_name: str, request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, _ = await _require_admin(request, db)
    if isinstance(current_user, Response):
        return current_user
    config = DB_TABLES.get(table_name)
    if config is None:
        return HTMLResponse("Tabla no permitida", status_code=404)
    model, columns, order_field = config
    result = await db.execute(select(model).order_by(desc(getattr(model, order_field))).limit(100))
    rows = result.scalars().all()
    header = "".join(f"<th>{_e(column)}</th>" for column in columns)
    body_rows = "".join(
        f"<tr>{''.join(f'<td>{_e(_render_column(item, column))}</td>' for column in columns)}</tr>"
        for item in rows
    ) or f"<tr><td colspan='{len(columns)}' class='muted'>Sin registros.</td></tr>"
    links = "".join(
        f"<a class='button secondary small' href='/admin/db/{name}'>{_e(name)}</a>"
        for name in DB_TABLES
    )
    body = f"""
    <section class="panel">
      <h1>Base de Datos: {_e(table_name)}</h1>
      <div class="toolbar wrap">{links}</div>
      <table>
        <thead><tr>{header}</tr></thead>
        <tbody>{body_rows}</tbody>
      </table>
    </section>
    """
    return HTMLResponse(_render_page("DB", body, request, current_user=current_user))


@admin_router.get("/ops", response_class=HTMLResponse)
async def ops_page(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, session_payload = await _require_admin(request, db)
    if isinstance(current_user, Response):
        return current_user
    runtime = _runtime_state(request)
    body = f"""
    <section class="panel">
      <h1>Operación</h1>
      <ul class="kv">
        <li><strong>Bot global</strong><span>{'Pausado' if runtime['bot_paused'] else 'Activo'}</span></li>
        <li><strong>Follow-ups</strong><span>{'Pausados' if runtime['followups_paused'] else 'Activos'}</span></li>
        <li><strong>IDs deduplicados</strong><span>{len(getattr(request.app.state, 'processed_webhook_ids', {}))}</span></li>
        <li><strong>Firmas outbound</strong><span>{len(getattr(request.app.state, 'recent_outbound_signatures', {}))}</span></li>
      </ul>
      <div class="actions">
        {_action_form('/admin/actions/pause-bot', 'Pausar bot', _csrf_input(session_payload))}
        {_action_form('/admin/actions/resume-bot', 'Reanudar bot', _csrf_input(session_payload))}
        {_action_form('/admin/actions/pause-followups', 'Pausar follow-ups', _csrf_input(session_payload))}
        {_action_form('/admin/actions/resume-followups', 'Reanudar follow-ups', _csrf_input(session_payload))}
        {_action_form('/admin/actions/clear-deduplication', 'Limpiar deduplicación', _csrf_input(session_payload))}
        {_action_form('/admin/actions/clear-rate-limit', 'Limpiar rate limit', _csrf_input(session_payload))}
        {_action_form('/admin/actions/clear-runtime', 'Limpiar runtime', _csrf_input(session_payload))}
        {_action_form('/admin/actions/run-janitor', 'Ejecutar janitor', _csrf_input(session_payload))}
        {_action_form('/admin/actions/sync-service-catalog', 'Sincronizar servicios', _csrf_input(session_payload))}
        {_action_form('/admin/actions/sync-fresha-catalog', 'Sincronizar Fresha CSV', _csrf_input(session_payload))}
        {_action_form('/admin/actions/reload-docs', 'Recargar docs', _csrf_input(session_payload))}
      </div>
    </section>
    """
    return HTMLResponse(_render_page("Operación", body, request, current_user=current_user))


@admin_router.post("/actions/{action_name}")
async def admin_action(action_name: str, request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, session_payload = await _require_admin(request, db)
    if isinstance(current_user, Response):
        return current_user
    form = await _parse_form(request)
    if not _valid_csrf(form, session_payload):
        return HTMLResponse("CSRF inválido", status_code=400)
    runtime = _runtime_state(request)
    message = "Acción no reconocida."
    entity_id = None
    if action_name == "pause-bot":
        runtime["bot_paused"] = True
        message = "Bot global pausado."
    elif action_name == "resume-bot":
        runtime["bot_paused"] = False
        message = "Bot global reanudado."
    elif action_name == "pause-followups":
        runtime["followups_paused"] = True
        message = "Follow-ups pausados."
    elif action_name == "resume-followups":
        runtime["followups_paused"] = False
        message = "Follow-ups reanudados."
    elif action_name == "clear-deduplication":
        getattr(request.app.state, "processed_webhook_ids", {}).clear()
        getattr(request.app.state, "recent_outbound_signatures", {}).clear()
        message = "Memoria de deduplicación limpiada."
    elif action_name == "clear-rate-limit":
        rate_limiter = getattr(request.app.state, "rate_limiter", None)
        if rate_limiter is not None and hasattr(rate_limiter, "_events"):
            rate_limiter._events.clear()
        message = "Rate limit en memoria limpiado."
    elif action_name == "clear-runtime":
        getattr(request.app.state, "processed_webhook_ids", {}).clear()
        getattr(request.app.state, "recent_outbound_signatures", {}).clear()
        getattr(request.app.state, "conversation_buffers", {}).clear()
        runtime["last_runtime_reset_at"] = datetime.now(UTC)
        message = "Runtime en memoria limpiado."
    elif action_name == "run-janitor":
        await purge_expired_records()
        runtime["last_janitor_run_at"] = datetime.now(UTC)
        message = "Janitor ejecutado."
    elif action_name == "reload-docs":
        get_knowledge_engine().reload()
        message = "Docs recargados."
    elif action_name == "sync-service-catalog":
        created, updated = await sync_service_catalog_from_docs(db, only_if_empty=False)
        message = f"Catálogo sincronizado desde docs. Creados: {created}. Actualizados: {updated}."
    elif action_name == "sync-fresha-catalog":
        settings = get_settings()
        created, updated = await sync_service_catalog_from_fresha_csv(
            db,
            settings.fresha_service_csv_path,
            only_if_exists=True,
        )
        message = (
            f"Catálogo sincronizado desde Fresha CSV. Creados: {created}. "
            f"Actualizados: {updated}. Archivo: {settings.fresha_service_csv_path}."
        )
    elif action_name == "clear-memory":
        whatsapp_id = form.get("whatsapp_id", "").strip()
        if not whatsapp_id:
            return _redirect("/admin/crm", "Falta whatsapp_id.")
        await db.execute(text("DELETE FROM interacciones WHERE whatsapp_id = :whatsapp_id"), {"whatsapp_id": whatsapp_id})
        await db.execute(text("DELETE FROM sesiones_memoria WHERE whatsapp_id = :whatsapp_id"), {"whatsapp_id": whatsapp_id})
        await db.execute(text("DELETE FROM citas_pendientes WHERE whatsapp_id = :whatsapp_id"), {"whatsapp_id": whatsapp_id})
        await db.execute(text("DELETE FROM citas_completadas WHERE whatsapp_id = :whatsapp_id"), {"whatsapp_id": whatsapp_id})
        entity_id = whatsapp_id
        message = "Memoria y chat borrados."
    await _audit(
        db,
        request,
        current_user,
        action=f"admin.action.{action_name}",
        entity_type="runtime_action",
        entity_id=entity_id,
        payload={"message": message},
    )
    await db.commit()
    referer = request.headers.get("referer") or ""
    back_to = "/admin/ops"
    if "/admin" in referer:
        back_to = referer
    if action_name == "clear-memory" and entity_id:
        back_to = "/admin/crm"
    return _redirect(back_to, message)


@admin_router.get("/audit", response_class=HTMLResponse)
async def audit_page(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    current_user, _ = await _require_admin(request, db)
    if isinstance(current_user, Response):
        return current_user
    result = await db.execute(select(AdminAuditLog).order_by(desc(AdminAuditLog.created_at)).limit(200))
    items = result.scalars().all()
    rows = "".join(
        f"<tr><td>{_format_datetime(item.created_at)}</td><td>{_e(item.action)}</td><td>{_e(item.entity_type or '-')}</td><td>{_e(item.entity_id or '-')}</td><td>{_e(item.ip_address or '-')}</td><td>{_e(_truncate(item.payload_json or '-', 120))}</td></tr>"
        for item in items
    ) or "<tr><td colspan='6' class='muted'>Sin auditoría.</td></tr>"
    body = f"""
    <section class="panel">
      <h1>Auditoría</h1>
      <table>
        <thead><tr><th>Fecha</th><th>Acción</th><th>Entidad</th><th>ID</th><th>IP</th><th>Payload</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """
    return HTMLResponse(_render_page("Auditoría", body, request, current_user=current_user))


async def bootstrap_admin_user() -> None:
    settings = get_settings()
    if not settings.admin_bootstrap_password.strip():
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AdminUser).where(AdminUser.username == settings.admin_bootstrap_username))
        existing = result.scalar_one_or_none()
        if existing is not None:
            if settings.admin_bootstrap_reset_existing:
                _apply_bootstrap_password(existing, settings.admin_bootstrap_password)
                await db.commit()
            return
        db.add(
            AdminUser(
                username=settings.admin_bootstrap_username,
                password_hash=hash_password(settings.admin_bootstrap_password),
                password_algo="scrypt",
                is_active=True,
                is_superadmin=True,
                temporary_password=True,
                must_rotate_password=True,
                password_expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        await db.commit()


def _apply_bootstrap_password(user: AdminUser, password: str) -> None:
    user.password_hash = hash_password(password)
    user.password_algo = "scrypt"
    user.is_active = True
    user.is_superadmin = True
    user.temporary_password = True
    user.must_rotate_password = True
    user.failed_login_attempts = 0
    user.locked_until = None
    user.password_expires_at = datetime.now(UTC) + timedelta(days=1)


def _render_page(title: str, body: str, request: Request, current_user: AdminUser | None) -> str:
    flash = request.query_params.get("flash", "")
    nav = ""
    if current_user is not None:
        nav = f"""
        <aside class="sidebar">
          <div class="brand">Sofía Admin</div>
          <nav>
            <a href="/admin">Dashboard</a>
            <a href="/admin/services">Servicios</a>
            <a href="/admin/crm">CRM</a>
            <a href="/admin/db/service_catalog">DB</a>
            <a href="/admin/ops">Operación</a>
            <a href="/admin/audit">Auditoría</a>
          </nav>
          <div class="session">
            <span>{_e(current_user.username)}</span>
            <form method="post" action="/admin/logout">
              <button type="submit" class="ghost">Salir</button>
            </form>
          </div>
        </aside>
        """
    flash_html = f"<div class='flash'>{_e(flash)}</div>" if flash else ""
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_e(title)} | Sofía Admin</title>
  <style>
    :root {{
      --bg: #f3efe7;
      --panel: #fffaf2;
      --ink: #1f2430;
      --muted: #6d727d;
      --line: #d8cfbf;
      --accent: #8b5e3c;
      --accent-2: #d1a26f;
      --danger: #9f2d2d;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Georgia, "Times New Roman", serif; background: linear-gradient(180deg, #f6f1e8 0%, #ece4d7 100%); color: var(--ink); }}
    a {{ color: inherit; }}
    .shell {{ display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }}
    .shell.login {{ grid-template-columns: 1fr; }}
    .sidebar {{ background: #1b1714; color: #f2ebde; padding: 24px 18px; display: flex; flex-direction: column; gap: 18px; }}
    .brand {{ font-size: 1.4rem; font-weight: 700; letter-spacing: .04em; }}
    .sidebar nav {{ display: grid; gap: 8px; }}
    .sidebar nav a {{ text-decoration: none; padding: 10px 12px; border-radius: 10px; background: rgba(255,255,255,.04); }}
    .sidebar nav a:hover {{ background: rgba(255,255,255,.1); }}
    .session {{ margin-top: auto; display: grid; gap: 10px; }}
    main {{ padding: 28px; display: grid; gap: 20px; }}
    .panel {{ background: rgba(255,250,242,.92); border: 1px solid var(--line); border-radius: 18px; padding: 20px; box-shadow: 0 14px 40px rgba(41, 33, 24, .08); }}
    .panel.narrow {{ max-width: 460px; margin: 8vh auto; }}
    h1, h2 {{ margin: 0 0 12px; }}
    .muted {{ color: var(--muted); }}
    .flash {{ background: #f5e9d2; border: 1px solid #e3cda4; padding: 12px 14px; border-radius: 12px; }}
    .grid {{ display: grid; gap: 20px; }}
    .grid.two {{ grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
    .cards {{ grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }}
    .metric {{ padding: 18px; border-radius: 14px; background: #f9f1e6; border: 1px solid var(--line); }}
    .metric strong {{ display: block; font-size: 1.9rem; }}
    .stack {{ display: grid; gap: 12px; }}
    .stack.compact {{ gap: 8px; }}
    label {{ display: grid; gap: 6px; font-size: .95rem; }}
    input, textarea, select {{ width: 100%; border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; font: inherit; background: white; }}
    button, .button {{ display: inline-flex; align-items: center; justify-content: center; border: 0; border-radius: 10px; padding: 10px 14px; cursor: pointer; background: var(--accent); color: white; text-decoration: none; font: inherit; }}
    button.secondary, .button.secondary {{ background: #e9dcc9; color: var(--ink); }}
    .ghost {{ background: transparent; color: inherit; border: 1px solid rgba(255,255,255,.3); }}
    .danger {{ background: var(--danger); }}
    .danger.ghost {{ background: transparent; color: var(--danger); border: 1px solid rgba(159,45,45,.4); }}
    .toolbar {{ display: flex; gap: 10px; align-items: center; margin-top: 12px; }}
    .toolbar.wrap {{ flex-wrap: wrap; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    .actions-cell {{ min-width: 160px; }}
    .table-wrap {{ width: 100%; overflow-x: auto; border: 1px solid var(--line); border-radius: 14px; background: rgba(255,255,255,.55); }}
    table {{ width: 100%; border-collapse: collapse; }}
    .wide-table {{ min-width: 1600px; }}
    th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .85rem; }}
    .center {{ text-align: center; }}
    .kv {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    .kv li {{ display: flex; justify-content: space-between; gap: 16px; border-bottom: 1px solid var(--line); padding-bottom: 8px; }}
    .inline {{ display: inline; }}
    .check {{ display: flex; align-items: center; gap: 10px; }}
    .check input {{ width: auto; }}
    @media (max-width: 860px) {{
      .shell {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; }}
      main {{ padding: 18px; }}
    }}
  </style>
</head>
<body>
  <div class="shell {'login' if current_user is None else ''}">
    {nav}
    <main>
      {flash_html}
      {body}
    </main>
  </div>
</body>
</html>"""


async def _require_admin(
    request: Request,
    db: AsyncSession,
    *,
    allow_password_rotation: bool = False,
) -> tuple[AdminUser | Response, dict[str, Any] | None]:
    settings = get_settings()
    if not settings.admin_webui_enabled:
        return HTMLResponse("Admin web UI disabled", status_code=503), None
    session_payload = _session_payload_from_request(request)
    if session_payload is None:
        return RedirectResponse("/admin/login", status_code=303), None
    try:
        user_uuid = uuid.UUID(session_payload["user_id"])
    except ValueError:
        response = RedirectResponse("/admin/login", status_code=303)
        _clear_session_cookie(response)
        return response, None
    result = await db.execute(select(AdminUser).where(AdminUser.id == user_uuid))
    current_user = result.scalar_one_or_none()
    if current_user is None or not current_user.is_active:
        response = RedirectResponse("/admin/login", status_code=303)
        _clear_session_cookie(response)
        return response, None
    if current_user.password_expires_at and current_user.password_expires_at < datetime.now(UTC):
        current_user.must_rotate_password = True
    if current_user.must_rotate_password and not allow_password_rotation:
        return RedirectResponse("/admin/password", status_code=303), None
    return current_user, session_payload


async def _audit(
    db: AsyncSession,
    request: Request,
    current_user: AdminUser | None,
    *,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    db.add(
        AdminAuditLog(
            admin_user_id=current_user.id if current_user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_json=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
            ip_address=request.client.host if request.client else None,
        )
    )


def _session_payload_from_request(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get(get_settings().admin_session_cookie_name)
    if not token:
        return None
    return read_admin_session_token(token)


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.admin_session_cookie_name,
        token,
        max_age=settings.admin_session_minutes * 60,
        httponly=True,
        samesite="strict",
        secure=not settings.debug,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(get_settings().admin_session_cookie_name, path="/")


async def _parse_form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8", errors="replace")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def _csrf_input(session_payload: dict[str, Any] | None) -> str:
    if session_payload is None:
        return ""
    return f'<input type="hidden" name="csrf_token" value="{_e(session_payload["csrf"])}">'


def _valid_csrf(form: dict[str, str], session_payload: dict[str, Any] | None) -> bool:
    if session_payload is None:
        return False
    return form.get("csrf_token", "") == session_payload.get("csrf", "")


def _redirect(path: str, message: str) -> RedirectResponse:
    separator = "&" if "?" in path else "?"
    return RedirectResponse(f"{path}{separator}{urlencode({'flash': message})}", status_code=303)


def _runtime_state(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "admin_runtime", None)
    if runtime is None:
        runtime = {
            "bot_paused": False,
            "followups_paused": False,
            "last_runtime_reset_at": None,
            "last_janitor_run_at": None,
        }
        request.app.state.admin_runtime = runtime
    return runtime


async def _scalar_count(db: AsyncSession, stmt: Any) -> int:
    result = await db.execute(stmt)
    return int(result.scalar() or 0)


async def _db_health(db: AsyncSession) -> bool:
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        return False
    return True


def _metric_card(label: str, value: Any) -> str:
    return f"<article class='metric'><span>{_e(label)}</span><strong>{_e(str(value))}</strong></article>"


def _action_form(action: str, label: str, csrf_html: str) -> str:
    return f"<form method='post' action='{_e(action)}'>{csrf_html}<button type='submit'>{_e(label)}</button></form>"


def _e(value: str | None) -> str:
    return html.escape(value or "", quote=True)


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return cleaned[:120] or "service"


def _service_type_options(selected: str, *, allow_blank: bool = True) -> str:
    options = [
        ("service", "Servicio"),
        ("promo", "Promoción"),
        ("package", "Paquete"),
        ("extra", "Extra"),
        ("nail_art", "Nail Art"),
    ]
    rendered = "".join(
        f"<option value='{_e(value)}' {'selected' if value == selected else ''}>{_e(label)}</option>"
        for value, label in options
    )
    if allow_blank:
        return rendered
    return rendered


def _service_category_options(categories: list[str], selected: str) -> str:
    return "".join(
        f"<option value='{_e(category)}' {'selected' if category == selected else ''}>{_e(category)}</option>"
        for category in categories
    )


def _service_matches_filters(
    item: ServiceCatalog,
    *,
    query: str,
    category: str,
    service_type: str,
) -> bool:
    if category and item.category != category:
        return False
    if service_type and item.service_type != service_type:
        return False
    if not query:
        return True
    haystack = " ".join(
        [
            str(item.id),
            item.external_service_id or "",
            item.name,
            item.slug,
            item.category,
            item.service_type,
            item.description or "",
        ]
    ).casefold()
    return query.casefold() in haystack


def _services_return_to(request: Request) -> str:
    query = request.url.query
    return "/admin/services" + (f"?{query}" if query else "")


def _safe_return_to(value: str) -> str:
    if value.startswith("/admin/services"):
        return value
    return "/admin/services"


def _service_row_html(item: ServiceCatalog, session_payload: dict[str, Any], return_to: str) -> str:
    update_form_id = f"update-service-{item.id}"
    delete_form_id = f"delete-service-{item.id}"
    return f"""
        <tr>
          <td class="mono">{_e(str(item.id))}</td>
          <td><input form="{update_form_id}" type="text" name="external_service_id" value="{_e(item.external_service_id or '')}" placeholder="Opcional"></td>
          <td>
            <input form="{update_form_id}" type="text" name="name" value="{_e(item.name)}" required>
            <input form="{update_form_id}" type="hidden" name="slug" value="{_e(item.slug)}">
          </td>
          <td><input form="{update_form_id}" type="number" name="base_price" value="{item.base_price}" step="0.01" min="0" required></td>
          <td><input form="{update_form_id}" type="number" name="duration_minutes" value="{item.duration_minutes}" min="0" required></td>
          <td><input form="{update_form_id}" type="number" name="purchase_price" value="{item.purchase_price}" step="0.01" min="0" required></td>
          <td><input form="{update_form_id}" type="number" name="additional_time_minutes" value="{item.additional_time_minutes}" min="0" required></td>
          <td><input form="{update_form_id}" type="number" name="tax_percent" value="{item.tax_percent}" step="0.01" min="0" required></td>
          <td><textarea form="{update_form_id}" name="description" rows="2">{_e(item.description or '')}</textarea></td>
          <td><input form="{update_form_id}" type="text" name="category" value="{_e(item.category)}" required></td>
          <td>
            <select form="{update_form_id}" name="service_type">
              {_service_type_options(item.service_type)}
            </select>
          </td>
          <td class="center"><input form="{update_form_id}" type="checkbox" name="is_active" {'checked' if item.is_active else ''}></td>
          <td class="actions-cell">
            <button form="{update_form_id}" type="submit">Guardar</button>
            <button form="{delete_form_id}" type="submit" class="danger ghost">Eliminar</button>
            <form id="{update_form_id}" method="post" action="/admin/services/{item.id}">
              {_csrf_input(session_payload)}
              <input type="hidden" name="return_to" value="{_e(return_to)}">
            </form>
            <form id="{delete_form_id}" method="post" action="/admin/services/{item.id}/delete">
              {_csrf_input(session_payload)}
              <input type="hidden" name="return_to" value="{_e(return_to)}">
            </form>
          </td>
        </tr>
    """


def _validate_password_strength(password: str, confirmation: str) -> str | None:
    if password != confirmation:
        return "La confirmación no coincide."
    if len(password) < 16:
        return "El password debe tener al menos 16 caracteres."
    categories = sum(
        bool(re.search(pattern, password))
        for pattern in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]")
    )
    if categories < 3:
        return "Usa mayúsculas, minúsculas, números y/o símbolos."
    return None


def _parse_service_payload(data: dict[str, str], *, import_mode: bool = False) -> tuple[str | None, dict[str, Any]]:
    name = data.get("name", "").strip()
    if not name:
        return "El nombre es obligatorio.", {}
    slug = _slugify(data.get("slug", "").strip() or name)
    try:
        base_price = float(str(data.get("base_price", "0")).strip())
        purchase_price = float(str(data.get("purchase_price", "0")).strip())
        duration_minutes = int(float(str(data.get("duration_minutes", "0")).strip()))
        additional_time_minutes = int(float(str(data.get("additional_time_minutes", "0")).strip()))
        tax_percent = float(str(data.get("tax_percent", "0")).strip())
    except ValueError:
        return "Precio o duración inválidos.", {}
    if base_price < 0 or purchase_price < 0 or duration_minutes < 0 or additional_time_minutes < 0 or tax_percent < 0:
        return "Precio, impuestos y tiempos deben ser positivos.", {}
    active_raw = str(data.get("is_active", "true")).strip().casefold()
    is_active = active_raw in {"1", "true", "yes", "si", "sí", "on"}
    service_type = data.get("service_type", "service").strip() or "service"
    payload = {
        "slug": slug,
        "name": name,
        "category": data.get("category", "General").strip() or "General",
        "service_type": service_type,
        "external_service_id": data.get("external_service_id", "").strip() or None,
        "description": data.get("description", "").strip() or None,
        "base_price": base_price,
        "purchase_price": purchase_price,
        "duration_minutes": duration_minutes,
        "additional_time_minutes": additional_time_minutes,
        "tax_percent": tax_percent,
        "is_active": is_active,
    }
    if import_mode:
        return None, payload
    return None, payload


def _parse_import_rows(format_name: str, payload_text: str) -> list[dict[str, str]]:
    if not payload_text.strip():
        raise ValueError("No hay contenido para importar.")
    if format_name == "json":
        payload = json.loads(payload_text)
        if isinstance(payload, dict):
            payload = payload.get("services", [])
        if not isinstance(payload, list):
            raise ValueError("El JSON debe ser una lista de servicios.")
        return [{str(key): "" if value is None else str(value) for key, value in item.items()} for item in payload if isinstance(item, dict)]
    if format_name == "csv":
        reader = csv.DictReader(io.StringIO(payload_text))
        return [{key: value or "" for key, value in row.items()} for row in reader]
    raise ValueError("Formato no soportado.")


def _render_column(item: Any, column: str) -> str:
    value = getattr(item, column)
    if isinstance(value, datetime):
        return _format_datetime(value)
    if value is None:
        return "-"
    return str(value)


def _safe_content(item: Interaccion) -> str:
    try:
        return item.content
    except ValueError:
        return "[No se pudo descifrar]"
