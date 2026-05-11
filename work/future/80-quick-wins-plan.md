# 80: Quick Wins & AI Catalog Import

## Summary

Implement high-value features: Low Stock Dashboard Widget, Export Service for
reports, and AI-powered Catalog Import (PDF-first, leveraging existing PO
parsing patterns).

## Acceptance Criteria

- [ ] Low Stock Widget shows products below reorder point on Dashboard
- [ ] Export Service generates CSV/PDF for inventory reports
- [ ] AI Catalog Import parses PDF catalogs (multi-page supported)
- [ ] User can preview extracted data before bulk importing

## Technical Approach

### Low Stock Widget

| File                                      | Change                    |
| ----------------------------------------- | ------------------------- |
| `backend/src/api/v1/endpoints/reports.py` | Add `/reports/low-stock`  |
| `frontend/src/app/dashboard/widgets/`     | `LowStockWidgetComponent` |
| `frontend/src/assets/i18n/*.json`         | Translations              |

### Export Service

| File                                           | Change                  |
| ---------------------------------------------- | ----------------------- |
| [NEW] `backend/src/services/export_service.py` | CSV/PDF generation      |
| `backend/src/api/v1/endpoints/reports.py`      | Add `/reports/export`   |
| `frontend/src/app/shared/`                     | Export button component |

### AI Catalog Import (PDF-First)

| File                                                     | Change                  |
| -------------------------------------------------------- | ----------------------- |
| [NEW] `backend/src/services/adk/agents/catalog/`         | Catalog parsing agent   |
| `backend/src/api/v1/endpoints/ai.py`                     | Add `/ai/parse-catalog` |
| [NEW] `frontend/src/app/products/catalog-import-dialog/` | Import dialog           |

**Supported PDF Types:**

- Price lists (SKU, Name, Price tables)
- Product catalogs (multi-page)
- Invoices/Quotes (reuse existing parsing patterns)

## Future Enhancements

- [ ] Website URL scraping for supplier product pages
- [ ] CSV column auto-mapping with AI suggestions

## Verification Plan

- [ ] Backend: `docker compose exec backend python -m pytest`
- [ ] Frontend: `npm test --prefix frontend`
- [ ] Manual: Test PDF upload with sample supplier catalog
