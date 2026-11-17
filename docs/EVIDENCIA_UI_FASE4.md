# Evidência UI — shell Fase 4

Rastreio da padronização de apresentação (sidebar + páginas). Não introduz funcionalidade de produto nova.

## Requisitos

| ID | Aceite | Evidência no código |
| --- | --- | --- |
| RF-UI-01 | Sidebar canônica em todas as páginas da Fase 4; item `active` conforme a rota atual | `web/templates/partials/sidebar.html`; flags `nav_*` em `web/app.py` |
| RF-UI-02 | Em viewport &lt; 992px: toggle abre/fecha o menu, backdrop fecha ao clique, Escape fecha; em ≥ 992px o toggle fica oculto e handlers são no-op | `web/templates/base.html`; media queries em `web/static/css/custom.css` |
| RF-UI-03 | Esqueleto de página coerente: seletor de paciente em `card fiap-card`; painéis de resultado com `dl`/`pre` + classes existentes; `<video>` com `fiap-video-preview` (sem `style` inline) | templates em `web/templates/fase4/` e `web/templates/alertas.html` |

## Nota de design (ADR não elegível)

A mudança alinha o markup Jinja às classes já definidas em `custom.css` (`.fiap-shell`, `.fiap-sidebar`, `.fiap-card`, `.fiap-code-block`, `.fiap-video-preview`, etc.), sem alterar contratos HTTP, modelo de domínio ou limites entre camadas. Pelo gate de elegibilidade de ADR, trata-se de **convenção de apresentação / baseline de UI** — **NOT ELIGIBLE** para ADR; este parágrafo registra a decisão de não abrir registro arquitetural.

## Riscos (ISO 31000 — escopo UI)

| ID | Risco | Tratamento | Status |
| --- | --- | --- | --- |
| R-UI-01 | XSS se `patient_id` for interpolado em `<script>` | Valor lido do DOM (`getElementById("patient_id").value`); saída via `textContent` / `encodeURIComponent` nas chamadas | Tratado |
| R-UI-02 | Backdrop/toggle ativos no desktop (≥ 992px) | CSS oculta `.fiap-sidebar-toggle`; JS `isDesktop()` faz no-op em click/backdrop/Escape e fecha no `resize` | Tratado |
