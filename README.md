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

1. HACS → three-dot menu → **Custom repositories**
2. Add this repository's URL, category **Integration**
3. Find **SpotBuddy** in HACS and click **Download**
4. Restart Home Assistant
5. Settings → Devices & Services → **Add integration** → **SpotBuddy**

### Manual

Copy `custom_components/spotbuddy/` into your Home Assistant `config/custom_components/` directory
and restart Home Assistant.

## Configuration

Everything is configured in the UI. The initial dialog asks for four things:

| Field | Meaning |
| --- | --- |
| Backend URL | Where your SpotBuddy API lives |
| API key | Sent as `X-Api-Key` |
| Latitude / Longitude | Pre-filled from Home Assistant's own location; decides which bidding zone your prices come from |

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

## Using it

Trigger an automation on `binary_sensor.spotbuddy_running`:

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

MIT. The integration's skeleton — entity base classes, platform patterns, config entry lifecycle and
CI workflow — is derived from [EV Smart Charging](https://github.com/jonasbkarlsson/ev_smart_charging)
by Jonas Karlsson, also MIT. Its scheduling logic and EV-specific handling are not used here:
SpotBuddy reads a plan committed by its own backend rather than optimising locally.
