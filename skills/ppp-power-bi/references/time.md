# Time: the service computes in UTC

- In the service `DateTimeZone.ToLocal`, `DateTime.LocalNow`, `DateTimeZone.LocalNow` and DAX `NOW()`/`TODAY()` return UTC-based values; after a refresh the local times are wrong. Do not use them. [D]
- Convert explicitly. The functions below implement the EU rule for Europe/Berlin (summer time from the last Sunday of March 01:00 UTC to the last Sunday of October 01:00 UTC) and were checked with a Python replica against IANA data 2025–2030: 210,336 hourly points, 6,573 shift boundaries, 0 deviations. [B] Other time zones: adapt offsets and rule and check the same way.

```powerquery
// fnUtcNachBerlin: UTC datetime → local time Europe/Berlin
(utc as datetime) as datetime =>
let
    jahr = Date.Year(utc),
    letzterSonntag = (monat as number) as datetime =>
        let ende = #date(jahr, monat, 31) in DateTime.From(Date.AddDays(ende, -Date.DayOfWeek(ende, Day.Sunday))),
    sommerAb  = letzterSonntag(3)  + #duration(0, 1, 0, 0),
    sommerBis = letzterSonntag(10) + #duration(0, 1, 0, 0),
    versatz   = if utc >= sommerAb and utc < sommerBis then 2 else 1
in
    utc + #duration(0, versatz, 0, 0)
```

```powerquery
// fnBerlinNachUtc: local time → UTC; unambiguous for full hours outside 02:00–03:00 on change days
(lokal as datetime) as datetime =>
let
    jahr = Date.Year(lokal),
    letzterSonntag = (monat as number) as datetime =>
        let ende = #date(jahr, monat, 31) in DateTime.From(Date.AddDays(ende, -Date.DayOfWeek(ende, Day.Sunday))),
    sommerAb  = letzterSonntag(3)  + #duration(0, 2, 0, 0),
    sommerBis = letzterSonntag(10) + #duration(0, 3, 0, 0),
    versatz   = if lokal >= sommerAb and lokal < sommerBis then 2 else 1
in
    lokal - #duration(0, versatz, 0, 0)
```

- ISO strings from JSON or REST to a UTC datetime: `DateTimeZone.RemoveZone(DateTimeZone.SwitchZone(DateTimeZone.FromText(x), 0))`.
- **Shift boundaries** come from local wall-clock times converted to UTC, never "start + 8 h": in clock-change nights a shift has 7 or 9 hours. Shift table per day: local boundaries (e.g. 06/14/22), `BeginnUtc`/`EndeUtc` with `fnBerlinNachUtc`, `Stunden = Duration.TotalHours(EndeUtc - BeginnUtc)`.
- Filters relative to "now": store `DateTimeZone.FixedUtcNow()` at refresh in a table `Stand` and show it as "data state" on every page.
- Test time logic **in the service after a refresh**, not only in Desktop.
- Python replicas compute in UTC as well: aware datetimes with the same `tzinfo` subtract as wall-clock time, so a 9-hour night comes out as 8 hours. [B]
