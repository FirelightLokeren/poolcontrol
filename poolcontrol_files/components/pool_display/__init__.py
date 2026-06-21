import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import ble_client
from esphome.const import CONF_ID

DEPENDENCIES = ["ble_client"]
AUTO_LOAD = []

pool_display_ns = cg.esphome_ns.namespace("pool_display")
PoolDisplay = pool_display_ns.class_(
    "PoolDisplay", cg.Component, ble_client.BLEClientNode
)

CONF_BRIGHTNESS = "brightness"
CONF_PAGE_SECONDS = "page_seconds"

CONFIG_SCHEMA = (
    cv.Schema({
        cv.GenerateID(): cv.declare_id(PoolDisplay),
        cv.Optional(CONF_BRIGHTNESS, default=70): cv.int_range(min=0, max=100),
        cv.Optional(CONF_PAGE_SECONDS, default=5): cv.int_range(min=2, max=60),
    })
    .extend(ble_client.BLE_CLIENT_SCHEMA)
    .extend(cv.COMPONENT_SCHEMA)
)

async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await ble_client.register_ble_node(var, config)
    cg.add(var.set_brightness(config[CONF_BRIGHTNESS]))
    cg.add(var.set_page_seconds(config[CONF_PAGE_SECONDS]))
