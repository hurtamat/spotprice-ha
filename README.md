# SpotBuddy for Home Assistant

Automate your appliances around day-ahead electricity spot prices. SpotBuddy works out your cheapest
hours server-side and publishes them to Home Assistant as entities; your automations act on them, so
anything Home Assistant controls becomes price-aware.

Keep your electricity supplier, keep your devices. No hardware to buy.

> **Status:** early. The integration is functional but has not been through a public release yet.

## Requirements

- Home Assistant 2024.4 or newer
- A SpotBuddy backend URL and API key
- [HACS](https://hacs.xyz/) for the easy install path

## Installation

### HACS

[![Open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hurtamat&repository=spotprice-ha&category=integration)

The badge opens your own Home Assistant with this repository pre-filled — no URLs to copy. Click
**Download**, then restart Home Assistant and add the integration:

[![Add the SpotBuddy integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=spotbuddy)

Doing it by hand instead: HACS → three-dot menu → **Custom repositories** → add this repository's
URL with category **Integration** → find **SpotBuddy** → **Download** → restart → Settings →
Devices & Services → **Add integration** → **SpotBuddy**.

### Manual

Copy `custom_components/spotbuddy/` into your Home Assistant `config/custom_components/` directory
and restart Home Assistant.

## Configuration

Everything is configured in the UI. The dialog asks for:

| Field | Required | Meaning |
| --- | --- | --- |
| Backend URL | yes | Where your SpotBuddy API lives |
| API key | yes | Sent as `X-Api-Key` |
| Latitude / Longitude | yes | Pre-filled from Home Assistant's own location; decides which bidding zone your prices come from |
| Controlled switch | no | Pick a switch and SpotBuddy turns it on and off for you. Leave it empty to drive things from your own automations instead. |

**Setting a controlled switch is the whole setup.** SpotBuddy switches that entity on when a cheap
block starts and off when it ends — no automation, no YAML. It only acts when the entity's state
differs from what the plan wants, so if you flip it by hand it stays flipped until the next
15-minute boundary.

## Entities

One config entry drives one appliance. Add the integration a second time for a second appliance.

### What SpotBuddy tells you

| Entity | Description |
| --- | --- |
| `binary_sensor.spotbuddy_running` | **The one that matters.** On during the cheap hours it picked. Attributes carry the zone and the full block list. |
| `sensor.spotbuddy_status` | `disabled`, `waiting_for_plan`, `no_plan`, `waiting_to_start`, `running`, `backend_unavailable` |
| `sensor.spotbuddy_current_price` | EUR/MWh for the current slot. The `curve` attribute holds today and tomorrow. |
| `sensor.spotbuddy_price_level` | `green`, `yellow` or `red` for the current slot |

### What you tell SpotBuddy

| Entity | Description |
| --- | --- |
| `number.spotbuddy_duration` | Hours of power the appliance needs |
| `time.spotbuddy_ready_by` | The deadline it must finish by |
| `switch.spotbuddy_continuous_block` | One unbroken run, or split for the absolute cheapest hours |
| `time.spotbuddy_unavailable_from` / `_to` | An optional do-not-run window |
| `switch.spotbuddy_enabled` | Master off switch |
| `button.spotbuddy_refresh_plan` | Fetch the plan again now |

## Using it without a controlled switch

If you left **Controlled switch** empty, drive things yourself from
`binary_sensor.spotbuddy_running`, which is on during the cheap hours.

### With the blueprint

[![Import the SpotBuddy blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fhurtamat%2Fspotprice-ha%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fspotbuddy%2Fcheap_hours_switch.yaml)

Import it, pick the run sensor and the device to control from dropdowns, and optionally add extra
conditions such as "somebody is home". No YAML.

### By hand

```yaml
automation:
  - alias: Boiler follows SpotBuddy
    triggers:
      - trigger: state
        entity_id: binary_sensor.spotbuddy_running
    actions:
      - action: "switch.turn_{{ 'on' if trigger.to_state.state == 'on' else 'off' }}"
        target:
          entity_id: switch.my_boiler_plug
```

The same sensor can drive any number of devices.

## How the plan is made

Day-ahead prices publish each afternoon. SpotBuddy picks your cheapest hours for the day and
**commits** that plan. The integration fetches it after midnight and again at 13:05 UTC, then
evaluates the stored plan against the clock every 15 minutes — it never re-optimises during the day.
That is deliberate: a plan that re-optimises as time passes will happily run an appliance for more
hours than you asked for.

## Development

CI runs hassfest, HACS validation and `black`. To work on it locally, symlink `custom_components/spotbuddy`
into your Home Assistant config directory.

## Licence and attribution

MIT — see [LICENSE](./LICENSE) and [NOTICE](./NOTICE).

The integration's skeleton — entity base classes, platform patterns, config entry lifecycle and CI
workflow — is derived from [EV Smart Charging](https://github.com/jonasbkarlsson/ev_smart_charging)
by Jonas Karlsson, also MIT. Its scheduling logic and EV-specific handling are not used here:
SpotBuddy reads a plan committed by its own backend rather than optimising locally.
