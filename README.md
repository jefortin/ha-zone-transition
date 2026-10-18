# Zone Transition

A Home Assistant custom integration that remembers where each person was and lets you
trigger automations when a person moves **from one zone to another**, for example
"left Work and arrived Home".

Time spent outside any zone (`not_home`) is skipped, so
`Work → not_home → Home` counts as one transition: **Work → Home**.

Requires Home Assistant 2026.10 or newer.

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories** → add this repo's URL, category **Integration**.
2. Install **Zone Transition** and restart Home Assistant.
3. Settings → Devices & services → **Add integration** → *Zone Transition* → **Submit**.

There is nothing to configure: every `person` is tracked automatically, including people
added later.

Manual install: copy `custom_components/zone_transition` into your `config/custom_components/`.

## Sensors (per person)

| Sensor | State | Attributes |
|---|---|---|
| **`<Person>` last known zone** | Zone the person is in, or the last one they were in while away | `person`, `zone`, `in_zone`, `arrived_at`, `left_at` |
| **`<Person>` previous zone** | Zone they were in before the last known zone | `person`, `zone` |

History is saved to disk, so it survives restarts.

## Automation trigger

### From the UI
Automation → **Add trigger** → *Zone Transition* → **Person moved between zones** →
pick the person(s), then optionally a *From zone* and a *To zone*.
Leave either zone empty to match any zone.

### YAML
```yaml
automation:
  - alias: "Arrived home from work"
    triggers:
      - trigger: zone_transition.moved
        target:
          entity_id: person.alex
        options:
          from_zone: zone.work
          to_zone: zone.home
    actions:
      - action: notify.mobile_app_my_phone
        data:
          message: >
            {{ trigger.to_zone_name }} reached
            ({{ (trigger.travel_seconds / 60) | round }} min trip).
```

### Trigger data
Available as `trigger.<key>` in the trigger, and as the data of the
`zone_transition_transition` event that is fired on every move:

| Key | Example |
|---|---|
| `entity_id` | `person.alex` |
| `from_zone` / `from_zone_name` | `zone.work` / `Work` |
| `to_zone` / `to_zone_name` | `zone.home` / `Home` |
| `left_at` / `arrived_at` | ISO timestamps (UTC) |
| `travel_seconds` | time spent between the two zones |

## Notes
- The trigger fires on **arrival** in the destination zone. If you want a heads-up when the person
  *leaves* the origin zone, use the built-in **Zone left** trigger instead, or combine both.
- Zones are matched by name, as the `person` entity reports them. Renaming a zone while the person
  is in it can make the history show the old name until their next move.
- Sensors of a deleted person are not removed automatically; delete them from the entity settings.

## License

MIT — see [LICENSE](LICENSE).
