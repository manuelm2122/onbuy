from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

RMV_DEFAULT = 1130.0


def _money(value: float, symbol: str = "S/") -> str:
    return f"{symbol} {value:,.2f}"


def _num(data: dict, key: str, default: float = 0.0, minimum: float = 0.0) -> float:
    raw = data.get(key)
    value = default if raw in (None, "") else float(raw)
    if value < minimum:
        raise ValueError(f"Valor inválido en '{key}'")
    return value


def _date(data: dict, key: str) -> date:
    try:
        return date.fromisoformat(str(data.get(key))[:10])
    except ValueError:
        raise ValueError(f"Fecha inválida en '{key}'")


def _month(data: dict, key: str) -> date:
    try:
        year, month = str(data.get(key))[:7].split("-")
        return date(int(year), int(month), 1)
    except ValueError:
        raise ValueError(f"Mes inválido en '{key}' (usa AAAA-MM)")


def _payments(text: str) -> dict:
    out = {}
    for line in (text or "").splitlines():
        parts = line.replace(",", "").split()
        if not parts:
            continue
        if len(parts) < 2:
            raise ValueError(f"Pago mal escrito: '{line.strip()}'. Usa: AAAA-MM monto")
        key = _month({"pago": parts[0]}, "pago").strftime("%Y-%m")
        out[key] = out.get(key, 0.0) + float(parts[1])
    return out


def _table(headers: list, rows: list) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def calc_beneficios(d: dict):
    ingreso, cese = _date(d, "fecha_ingreso"), _date(d, "fecha_cese")
    if cese <= ingreso:
        raise ValueError("La fecha de cese debe ser posterior a la de ingreso")
    sueldo = _num(d, "sueldo", minimum=1)
    rmv = _num(d, "rmv", RMV_DEFAULT, 1)
    asignacion = round(rmv * 0.10, 2) if d.get("asignacion_familiar") else 0.0
    rc = sueldo + asignacion
    fin = cese + timedelta(days=1)
    servicio = relativedelta(fin, ingreso)
    con_un_mes = servicio.years > 0 or servicio.months >= 1

    if 5 <= cese.month <= 10:
        sem_cts = date(cese.year, 5, 1)
    else:
        sem_cts = date(cese.year if cese.month >= 11 else cese.year - 1, 11, 1)
    t_cts = relativedelta(fin, max(ingreso, sem_cts))
    rc_cts = rc + rc / 6
    cts = (rc_cts / 12 * t_cts.months + rc_cts / 360 * t_cts.days) if con_un_mes else 0.0

    first_month = 1 if cese.month <= 6 else 7
    meses_grati = 0
    for m in range(first_month, cese.month + 1):
        inicio_mes = date(cese.year, m, 1)
        fin_mes = inicio_mes + relativedelta(months=1) - timedelta(days=1)
        if ingreso <= inicio_mes and cese >= fin_mes:
            meses_grati += 1
    grati = rc / 6 * meses_grati if con_un_mes else 0.0
    bonif = grati * 0.09

    t_vac = relativedelta(fin, ingreso + relativedelta(years=servicio.years))
    vac_truncas = (rc / 12 * t_vac.months + rc / 360 * t_vac.days) if con_un_mes else 0.0
    dias_pend = _num(d, "vacaciones_pendientes_dias")
    vac_pend = rc / 30 * dias_pend

    indemn = 0.0
    if d.get("despido_arbitrario") and (servicio.years > 0 or servicio.months >= 3):
        anios = servicio.years + servicio.months / 12 + servicio.days / 360
        indemn = min(1.5 * rc * anios, 12 * rc)

    rows = [
        ["CTS trunca del semestre en curso", f"{t_cts.months} meses y {t_cts.days} días", _money(cts)],
        ["Gratificación trunca", f"{meses_grati} meses completos", _money(grati)],
        ["Bonificación extraordinaria 9% (Ley 30334)", "sobre la gratificación trunca", _money(bonif)],
        ["Vacaciones truncas", f"{t_vac.months} meses y {t_vac.days} días", _money(vac_truncas)],
    ]
    if dias_pend:
        rows.append(["Vacaciones no gozadas", f"{dias_pend:g} días", _money(vac_pend)])
    if d.get("despido_arbitrario"):
        rows.append(["Indemnización por despido arbitrario", "1.5 remuneraciones por año, tope 12", _money(indemn)])
    total = cts + grati + bonif + vac_truncas + vac_pend + indemn
    rows.append(["**TOTAL BRUTO**", "", f"**{_money(total)}**"])

    datos = _table(["Dato", "Valor"], [
        ["Fecha de ingreso", ingreso.strftime("%d/%m/%Y")],
        ["Fecha de cese", cese.strftime("%d/%m/%Y")],
        ["Tiempo de servicios", f"{servicio.years} años, {servicio.months} meses y {servicio.days} días"],
        ["Remuneración mensual", _money(sueldo)],
        ["Asignación familiar (10% de la RMV de " + _money(rmv) + ")", _money(asignacion)],
        ["Remuneración computable", _money(rc)],
        ["Remuneración computable para CTS (incluye 1/6 de gratificación)", _money(rc_cts)],
    ])
    notas = (
        "- Régimen laboral general de la actividad privada (D.S. 001-97-TR, Ley 27735, D. Leg. 713, D.S. 003-97-TR). "
        "La micro y pequeña empresa y otros regímenes especiales tienen reglas distintas.\n"
        "- Se asume remuneración fija y que la última gratificación fue de una remuneración completa.\n"
        "- Montos brutos: no incluye descuentos de AFP/ONP ni impuesto a la renta, ni CTS o gratificaciones de períodos anteriores que estuvieran impagas."
    )
    return "Liquidación de beneficios sociales", f"### Datos\n{datos}\n\n### Liquidación\n{_table(['Concepto', 'Base', 'Monto'], rows)}\n\n### Notas\n{notas}"


def calc_intereses(d: dict):
    capital = _num(d, "capital", minimum=0.01)
    inicio, fin = _date(d, "fecha_inicio"), _date(d, "fecha_fin")
    dias = (fin - inicio).days
    if dias <= 0:
        raise ValueError("La fecha final debe ser posterior a la inicial")
    laboral = d.get("tipo") == "laboral"
    f_ini, f_fin = _num(d, "factor_inicio"), _num(d, "factor_fin")
    if f_ini and f_fin:
        if f_fin < f_ini:
            raise ValueError("El factor acumulado final no puede ser menor que el inicial")
        interes = capital * ((f_fin - f_ini) if laboral else (f_fin / f_ini - 1))
        metodo = f"Factores acumulados de la SBS: inicial {f_ini:.5f}, final {f_fin:.5f}"
        formula = "capital × (factor final − factor inicial)" if laboral else "capital × (factor final ÷ factor inicial − 1)"
    else:
        tasa = _num(d, "tasa_anual", minimum=0.0001) / 100
        if laboral:
            interes = capital * ((1 + tasa) ** (1 / 360) - 1) * dias
            formula = "capital × factor diario × días (sin capitalización)"
        else:
            interes = capital * ((1 + tasa) ** (dias / 360) - 1)
            formula = "capital × ((1 + tasa)^(días/360) − 1)"
        metodo = f"Tasa de interés legal anual constante de {tasa * 100:.4f}%"
    tipo = "Tasa de interés legal laboral (no capitalizable, D. Ley 25920)" if laboral else "Tasa de interés legal efectiva (art. 1244 del Código Civil)"
    tabla = _table(["Concepto", "Valor"], [
        ["Capital", _money(capital)],
        ["Período", f"{inicio.strftime('%d/%m/%Y')} al {fin.strftime('%d/%m/%Y')} ({dias} días)"],
        ["Tipo de interés", tipo],
        ["Método", metodo],
        ["Fórmula", formula],
        ["Intereses", _money(interes)],
        ["**Capital + intereses**", f"**{_money(capital + interes)}**"],
    ])
    notas = (
        "- El resultado exacto se obtiene con los factores acumulados que publica la SBS para cada fecha "
        "(sbs.gob.pe → Tasa de interés legal). Con una tasa anual constante el resultado es una aproximación, porque la tasa legal varía cada día.\n"
        "- Moneda nacional. Para deudas en dólares usa los factores de moneda extranjera."
    )
    return "Liquidación de intereses legales", f"{tabla}\n\n### Notas\n{notas}"


def _ledger(d: dict, monto_key: str, concepto: str, symbol: str):
    monto = _num(d, monto_key, minimum=0.01)
    inicio, fin = _month(d, "mes_inicio"), _month(d, "mes_fin")
    if fin < inicio:
        raise ValueError("El mes final debe ser igual o posterior al inicial")
    pagos = _payments(d.get("pagos"))
    rows, acumulado, total_pagado, impagos, cursor = [], 0.0, 0.0, 0, inicio
    while cursor <= fin:
        key = cursor.strftime("%Y-%m")
        pagado = pagos.pop(key, 0.0)
        acumulado += monto - pagado
        total_pagado += pagado
        impagos += 1 if monto - pagado > 0.005 else 0
        rows.append([cursor.strftime("%m/%Y"), _money(monto, symbol), _money(pagado, symbol), _money(monto - pagado, symbol), _money(acumulado, symbol)])
        cursor += relativedelta(months=1)
    if len(rows) > 240:
        raise ValueError("El período máximo es de 20 años")
    fuera = sum(pagos.values())
    return monto, rows, acumulado - fuera, total_pagado + fuera, fuera, impagos, _table(["Mes", concepto, "Pagado", "Saldo del mes", "Saldo acumulado"], rows)


def calc_alimentos(d: dict):
    monto, rows, saldo, pagado, fuera, _, tabla = _ledger(d, "monto_mensual", "Pensión", "S/")
    resumen = _table(["Concepto", "Monto"], [
        ["Pensión mensual fijada", _money(monto)],
        ["Meses liquidados", len(rows)],
        ["Total devengado", _money(monto * len(rows))],
        ["Total pagado", _money(pagado)],
        ["**Pensiones devengadas pendientes**", f"**{_money(saldo)}**"],
    ])
    notas = (
        "- Las pensiones se devengan desde el día siguiente a la notificación de la demanda (art. 568 del Código Procesal Civil).\n"
        "- No incluye intereses legales: calcúlalos con la calculadora de intereses sobre este saldo.\n"
        + (f"- Se descontaron {_money(fuera)} de pagos registrados fuera del período.\n" if fuera else "")
    )
    return "Liquidación de pensiones de alimentos devengadas", f"### Resumen\n{resumen}\n\n### Detalle mes a mes\n{tabla}\n\n### Notas\n{notas}"


def calc_alquileres(d: dict):
    symbol = "US$" if d.get("moneda") == "USD" else "S/"
    renta, rows, saldo, pagado, fuera, meses_impagos, tabla = _ledger(d, "renta_mensual", "Renta", symbol)
    penalidad = _num(d, "penalidad_mensual")
    garantia = _num(d, "garantia")
    total_penalidad = penalidad * meses_impagos
    total = saldo + total_penalidad - garantia
    resumen_rows = [
        ["Renta mensual", _money(renta, symbol)],
        ["Meses liquidados", len(rows)],
        ["Total de rentas del período", _money(renta * len(rows), symbol)],
        ["Total pagado", _money(pagado, symbol)],
        ["Rentas adeudadas", _money(saldo, symbol)],
    ]
    if penalidad:
        resumen_rows.append([f"Penalidad pactada ({meses_impagos} meses con saldo × {_money(penalidad, symbol)})", _money(total_penalidad, symbol)])
    if garantia:
        resumen_rows.append(["Garantía a descontar", f"- {_money(garantia, symbol)}"])
    resumen_rows.append(["**TOTAL ADEUDADO**", f"**{_money(total, symbol)}**"])
    notas = (
        "- La penalidad solo procede si está pactada en el contrato; la garantía se descuenta si el arrendador decide aplicarla a la deuda.\n"
        "- No incluye intereses, servicios (luz, agua, mantenimiento) ni daños al inmueble.\n"
        + (f"- Se descontaron {_money(fuera, symbol)} de pagos registrados fuera del período.\n" if fuera else "")
    )
    return "Liquidación de alquileres impagos", f"### Resumen\n{_table(['Concepto', 'Monto'], resumen_rows)}\n\n### Detalle mes a mes\n{tabla}\n\n### Notas\n{notas}"


CALCULATORS = {
    "beneficios": calc_beneficios,
    "intereses": calc_intereses,
    "alimentos": calc_alimentos,
    "alquileres": calc_alquileres,
}
