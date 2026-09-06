/**
 * SpotBuddy Lovelace card.
 *
 * The day-ahead price curve as bars coloured by price level, with every committed run
 * block shaded on top of it. A split (non-continuous) plan has several blocks, so the
 * shading is drawn per block rather than as one span.
 *
 * Plain custom element and inline SVG on purpose: the integration ships this file as-is,
 * so there is no bundler, no chart library and nothing to fetch at runtime.
 */

const CARD_TYPE = "spotbuddy-card";

// Matches the backend's PriceColor slugs. Falls back to Home Assistant's own theme
// variables so the card follows a user's dark or custom theme.
const LEVEL_COLOR = {
  green: "var(--success-color, #2e9e5b)",
  yellow: "var(--warning-color, #e0a325)",
  red: "var(--error-color, #d9453b)",
};
const UNCLASSIFIED_COLOR = "var(--disabled-text-color, #9a9a9a)";

// The curve attribute carries the backend's PriceColor as an int (0 green, 1 yellow, 2 red),
// while the price level sensor publishes the slug. Accept either.
const LEVEL_BY_INDEX = ["green", "yellow", "red"];
const levelColor = (level) =>
  LEVEL_COLOR[typeof level === "number" ? LEVEL_BY_INDEX[level] : level] ?? UNCLASSIFIED_COLOR;

// Coordinate space of the plot. The SVG scales to the card width from here.
const VIEW = { w: 600, h: 200, padTop: 8, padBottom: 22, padLeft: 34, padRight: 6 };

const pad2 = (n) => String(n).padStart(2, "0");

/** "HH:MM" in the viewer's own timezone. The wire is UTC; this is the only place it lands. */
function localTime(iso) {
  const d = new Date(iso);
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

/** "Mon 04:00" for a moment far enough away that the hour alone is ambiguous. */
function localDayTime(iso) {
  const d = new Date(iso);
  const day = d.toLocaleDateString(undefined, { weekday: "short" });
  return `${day} ${localTime(iso)}`;
}

class SpotBuddyCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._hass = null;
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("spotbuddy-card: an `entity` is required (the Running binary sensor)");
    }
    if (!config.entity.startsWith("binary_sensor.")) {
      throw new Error("spotbuddy-card: `entity` must be the SpotBuddy Running binary sensor");
    }
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 5;
  }

  /** Prefills the picker with the first SpotBuddy running sensor found, so the card works unconfigured. */
  static getStubConfig(hass) {
    const entity = Object.keys(hass.states).find(
      (id) => id.startsWith("binary_sensor.") && id.includes("spotbuddy") && id.endsWith("_running"),
    );
    return { type: `custom:${CARD_TYPE}`, entity: entity ?? "" };
  }

  /**
   * The price sensor belonging to the same device as the configured binary sensor.
   * One config entry is one appliance, so this is what keeps two appliances apart.
   * `price_entity` in the config overrides it; the id-shaped guess is the last resort
   * for installs where the frontend has no entity registry loaded.
   */
  _findPriceEntity() {
    if (this._config.price_entity) return this._config.price_entity;

    const registry = this._hass.entities;
    const deviceId = registry?.[this._config.entity]?.device_id;
    if (deviceId) {
      const sibling = Object.keys(registry).find(
        (id) =>
          registry[id].device_id === deviceId &&
          id.startsWith("sensor.") &&
          Array.isArray(this._hass.states[id]?.attributes?.curve),
      );
      if (sibling) return sibling;
    }

    return this._config.entity
      .replace(/^binary_sensor\./, "sensor.")
      .replace(/_running$/, "_current_price");
  }

  _render() {
    if (!this._config || !this._hass) return;

    const running = this._hass.states[this._config.entity];
    if (!running) {
      this.shadowRoot.innerHTML = this._shell(
        `<div class="state">Entity ${this._config.entity} not found.</div>`,
      );
      return;
    }

    const price = this._hass.states[this._findPriceEntity()];
    const curve = price?.attributes?.curve ?? [];
    const blocks = running.attributes?.blocks ?? [];

    const title =
      this._config.title ??
      this._hass.states[this._config.entity].attributes.friendly_name ??
      "SpotBuddy";

    if (curve.length === 0) {
      this.shadowRoot.innerHTML = this._shell(
        `<div class="state">No price curve yet. Press <b>Refresh plan</b> once the backend has prices.</div>`,
        title,
        running,
      );
      return;
    }

    this.shadowRoot.innerHTML = this._shell(this._chart(curve, blocks), title, running);
  }

  /** Card chrome: title, the next-start line, and whatever body is passed in. */
  _shell(body, title = "SpotBuddy", running = null) {
    const zone = running?.attributes?.zone_name;
    const subtitle = this._subtitle(running);

    return `
      <style>
        ha-card { padding: 14px 16px 10px; }
        .head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
        .title { font-size: 16px; font-weight: 500; }
        .zone { font-size: 12px; color: var(--secondary-text-color); }
        .sub { margin-top: 2px; font-size: 13px; color: var(--secondary-text-color); }
        .sub b { color: var(--primary-text-color); font-weight: 500; }
        svg { width: 100%; height: auto; display: block; margin-top: 6px; }
        .legend { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 4px;
                  font-size: 12px; color: var(--secondary-text-color); align-items: center; }
        .dot { width: 9px; height: 9px; border-radius: 2px; display: inline-block; margin-right: 5px; }
        .state { padding: 18px 0; color: var(--secondary-text-color); font-size: 13px; }
      </style>
      <ha-card>
        <div class="head">
          <span class="title">${title}</span>
          ${zone ? `<span class="zone">${zone}</span>` : ""}
        </div>
        ${subtitle ? `<div class="sub">${subtitle}</div>` : ""}
        ${body}
      </ha-card>
    `;
  }

  /** "Runs 02:00 - 05:00" / "Running until 05:00" / "Nothing planned", from the blocks themselves. */
  _subtitle(running) {
    if (!running) return "";
    const blocks = running.attributes?.blocks ?? [];
    if (blocks.length === 0) return "Nothing planned";

    const now = Date.now();
    const active = blocks.find(
      (b) => now >= Date.parse(b.start_utc) && now < Date.parse(b.end_utc),
    );
    if (active) return `Running until <b>${localTime(active.end_utc)}</b>`;

    const next = blocks
      .filter((b) => Date.parse(b.start_utc) >= now)
      .sort((a, b) => Date.parse(a.start_utc) - Date.parse(b.start_utc))[0];
    if (!next) return "Nothing planned";

    const soon = Date.parse(next.start_utc) - now < 18 * 3600 * 1000;
    const label = soon ? localTime(next.start_utc) : localDayTime(next.start_utc);
    const total = blocks.length > 1 ? ` · ${blocks.length} blocks` : "";
    return `Starts <b>${label}</b>${total}`;
  }

  _chart(curve, blocks) {
    const slots = curve
      .map((p) => ({
        start: Date.parse(p.start_utc),
        end: Date.parse(p.end_utc),
        value: Number(p.eur_per_mwh),
        level: p.level,
      }))
      .filter((s) => Number.isFinite(s.start) && Number.isFinite(s.end))
      .sort((a, b) => a.start - b.start);

    if (slots.length === 0) return `<div class="state">Price curve could not be read.</div>`;

    const t0 = slots[0].start;
    const t1 = slots[slots.length - 1].end;
    const values = slots.map((s) => s.value).filter(Number.isFinite);
    // Negative day-ahead prices happen, so the baseline is the lower of zero and the minimum.
    const vMin = Math.min(0, ...values);
    const vMax = Math.max(...values, vMin + 1);

    const plotW = VIEW.w - VIEW.padLeft - VIEW.padRight;
    const plotH = VIEW.h - VIEW.padTop - VIEW.padBottom;
    const x = (t) => VIEW.padLeft + ((t - t0) / (t1 - t0)) * plotW;
    const y = (v) => VIEW.padTop + (1 - (v - vMin) / (vMax - vMin)) * plotH;
    const baseline = y(Math.max(vMin, 0));

    // Run blocks first, so the bars sit on top of the shading rather than under it.
    const blockShapes = (blocks ?? [])
      .map((b) => {
        const bs = Date.parse(b.start_utc);
        const be = Date.parse(b.end_utc);
        if (!Number.isFinite(bs) || !Number.isFinite(be)) return "";
        // A block can start before the curve does, or run past its end; clip to the plot.
        const left = x(Math.max(bs, t0));
        const right = x(Math.min(be, t1));
        if (right <= left) return "";
        return `
          <rect x="${left.toFixed(1)}" y="${VIEW.padTop}" width="${(right - left).toFixed(1)}"
                height="${plotH}" fill="var(--primary-color)" opacity="0.14" />
          <rect x="${left.toFixed(1)}" y="${(VIEW.padTop + plotH - 3).toFixed(1)}"
                width="${(right - left).toFixed(1)}" height="3" fill="var(--primary-color)" rx="1.5" />
        `;
      })
      .join("");

    const bars = slots
      .map((s) => {
        const left = x(s.start);
        const width = Math.max(x(s.end) - left - 0.5, 0.6);
        const top = Math.min(y(s.value), baseline);
        const height = Math.max(Math.abs(baseline - y(s.value)), 0.8);
        const color = levelColor(s.level);
        return `<rect x="${left.toFixed(1)}" y="${top.toFixed(1)}" width="${width.toFixed(1)}"
                      height="${height.toFixed(1)}" fill="${color}" rx="0.8">
                  <title>${localTime(new Date(s.start).toISOString())} · ${s.value.toFixed(0)} EUR/MWh</title>
                </rect>`;
      })
      .join("");

    // A label every 6 hours of local wall clock, walked from the first whole hour.
    const ticks = [];
    const cursor = new Date(t0);
    cursor.setMinutes(0, 0, 0);
    while (cursor.getTime() <= t1) {
      if (cursor.getHours() % 6 === 0 && cursor.getTime() >= t0) {
        ticks.push(
          `<text x="${x(cursor.getTime()).toFixed(1)}" y="${VIEW.h - 6}" text-anchor="middle"
                 font-size="10" fill="var(--secondary-text-color)">${pad2(cursor.getHours())}</text>`,
        );
      }
      cursor.setHours(cursor.getHours() + 1);
    }

    const now = Date.now();
    const nowLine =
      now >= t0 && now <= t1
        ? `<line x1="${x(now).toFixed(1)}" y1="${VIEW.padTop}" x2="${x(now).toFixed(1)}"
                 y2="${VIEW.padTop + plotH}" stroke="var(--primary-text-color)"
                 stroke-width="1" stroke-dasharray="3 3" opacity="0.55" />`
        : "";

    const axis = [vMax, vMin]
      .map(
        (v) => `<text x="${VIEW.padLeft - 6}" y="${(y(v) + 3).toFixed(1)}" text-anchor="end"
                      font-size="10" fill="var(--secondary-text-color)">${v.toFixed(0)}</text>`,
      )
      .join("");

    return `
      <svg viewBox="0 0 ${VIEW.w} ${VIEW.h}" preserveAspectRatio="xMidYMid meet" role="img"
           aria-label="Price curve with the planned run blocks highlighted">
        <line x1="${VIEW.padLeft}" y1="${baseline.toFixed(1)}" x2="${VIEW.w - VIEW.padRight}"
              y2="${baseline.toFixed(1)}" stroke="var(--divider-color)" stroke-width="1" />
        ${blockShapes}
        ${bars}
        ${nowLine}
        ${axis}
        ${ticks.join("")}
      </svg>
      <div class="legend">
        <span><i class="dot" style="background:${LEVEL_COLOR.green}"></i>Cheap</span>
        <span><i class="dot" style="background:${LEVEL_COLOR.yellow}"></i>Average</span>
        <span><i class="dot" style="background:${LEVEL_COLOR.red}"></i>Expensive</span>
        <span><i class="dot" style="background:var(--primary-color);opacity:.4"></i>Running</span>
        <span style="margin-left:auto">EUR/MWh · local time</span>
      </div>
    `;
  }
}

if (!customElements.get(CARD_TYPE)) {
  customElements.define(CARD_TYPE, SpotBuddyCard);
}

// Puts the card in the "Add card" picker, so nobody has to write YAML by hand.
window.customCards = window.customCards || [];
window.customCards.push({
  type: CARD_TYPE,
  name: "SpotBuddy",
  description: "Day-ahead prices with your planned cheap hours highlighted",
  preview: true,
  documentationURL: "https://github.com/hurtamat/spotprice-ha",
});
