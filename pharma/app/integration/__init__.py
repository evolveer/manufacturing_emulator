"""
Integration layer: adapters for ERP, MES, and PCS upstream systems.
All calls are best-effort unless PHARMA_INTEGRATION_STRICT=true.
"""
from .orchestrator import (
    get_system_health,
    on_order_created,
    on_order_sent_to_mes,
    on_batch_created,
    on_step_started,
    on_parameter_captured,
    on_step_completed,
    on_deviation_opened,
    on_batch_completed,
    on_batch_released,
    on_batch_rejected,
    get_live_machine_data,
    get_mes_production_summary,
    get_mes_quality_summary,
    get_erp_inventory_snapshot,
    get_erp_products,
)

__all__ = [
    "get_system_health",
    "on_order_created",
    "on_order_sent_to_mes",
    "on_batch_created",
    "on_step_started",
    "on_parameter_captured",
    "on_step_completed",
    "on_deviation_opened",
    "on_batch_completed",
    "on_batch_released",
    "on_batch_rejected",
    "get_live_machine_data",
    "get_mes_production_summary",
    "get_mes_quality_summary",
    "get_erp_inventory_snapshot",
    "get_erp_products",
]
