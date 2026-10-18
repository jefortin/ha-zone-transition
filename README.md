# Zone Transition

A Home Assistant custom integration that remembers where a person was and lets you
trigger automations when they move **from one zone to another**, for example
"left Work and arrived Home".

Time spent outside any zone (`not_home`) is skipped, so
`Work → not_home → Home` counts as one transition: **Work → Home**.

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories** → add this repo's URL, category **Integration**.
2. Install **Zone Transition** and restart Home Assistant.
3. Settings → Devices & services → **Add integration** → *Zone Transition* → pick a person.
   Repeat for each person you want to track.

Manual install: copy `custom_components/zone_transition` into your `config/custom_components/`.

## What you get (per person)

A device named after the person, with these sensors:

| Sensor | State | Attributes |
|---|---|---|
| **Last known zone** | Zone the person is in, or the last one they were in while away | `zone`, `in_zone`, `arrived_at`, `left_at` |
| **Previous zone** | Zone they were in before the last known zone | `zone` |

History is saved to disk, so it survives restarts.

## Automation trigger

### From the UI
Automation → Add trigger → **Device** → pick the person's device →
**Moved from one zone to another** → optionally set *From zone* and *To zone*.
Leave either one empty to match any zone.

### YAML
```yaml
automation:
  - alias: "Arrived home from work"
    triggers:
      - trigger: event
        event_type: zone_transition_transition
        event_data:
          entity_id: person.alex
          from_zone: zone.work
          to_zone: zone.home
    actions:
      - action: notify.mobile_app_my_phone
        data:
          message: >
            {{ trigger.event.data.to_zone_name }} reached
            ({{ (trigger.event.data.travel_seconds / 60) | round }} min trip).
```

### Event data
`zone_transition_transition` is fired with:

| Key | Example |
|---|---|
| `entity_id` | `person.alex` |
| `device_id` | device id of the tracker |
| `from_zone` / `from_zone_name` | `zone.work` / `Work` |
| `to_zone` / `to_zone_name` | `zone.home` / `Home` |
| `left_at` / `arrived_at` | ISO timestamps (UTC) |
| `travel_seconds` | time spent between the two zones |

## Notes
- The trigger fires on **arrival** in the destination zone. If you want a heads-up when the person
  *leaves* the origin zone, use the standard Zone trigger (`leave`) instead, or combine both.
- Zones are matched by name, as the `person` entity reports them. Renaming a zone while the person
  is in it can make the history show the old name until their next move.

## License

MIT — see [LICENSE](LICENSE).
