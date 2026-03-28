"""Quality Score helper functions — shared between analytics and export routers."""


def build_subcomponent_issues(kw):
    """Generate issues list from actual QS subcomponent data."""
    issues = []
    if (kw.historical_search_predicted_ctr or 0) == 1:
        issues.append("Oczekiwany CTR: poniżej średniej")
    if (kw.historical_creative_quality or 0) == 1:
        issues.append("Trafność reklamy: poniżej średniej")
    if (kw.historical_landing_page_quality or 0) == 1:
        issues.append("Strona docelowa: poniżej średniej")
    # Fallback when no subcomponent data available
    if not issues and kw.quality_score and kw.quality_score <= 3:
        if (kw.ctr or 0) < 2.0:
            issues.append("Niski CTR — treść reklamy może nie pasować")
    if (kw.cost_micros or 0) > 50_000_000 and (kw.conversions or 0) == 0:
        issues.append("Wysokie wydatki, brak konwersji — problem ze stroną?")
    return issues


def get_primary_issue(kw):
    """Return the weakest QS subcomponent name or None."""
    components = {
        "expected_ctr": kw.historical_search_predicted_ctr,
        "ad_relevance": kw.historical_creative_quality,
        "landing_page": kw.historical_landing_page_quality,
    }
    valid = [(k, v) for k, v in components.items() if v is not None]
    if not valid:
        return None
    worst = min(valid, key=lambda x: x[1])
    return worst[0] if worst[1] <= 2 else None


def build_recommendation(kw):
    """Contextual recommendation based on weakest subcomponent + performance data."""
    primary = get_primary_issue(kw)
    if not primary:
        return "Sprawdź dopasowanie reklamy do słowa kluczowego"

    ctr = kw.ctr or 0
    cost = (kw.cost_micros or 0) / 1_000_000
    convs = kw.conversions or 0
    is_lost = kw.search_rank_lost_is or 0

    if primary == "expected_ctr":
        if ctr >= 5:
            return f"CTR={ctr:.1f}% ale Expected CTR poniżej średniej — benchmark wyższy, rozważ SKAG lub DKI"
        elif cost > 50 and convs == 0:
            return f"Niski CTR + {cost:.0f} zł bez konwersji — rozważ pauzę lub SKAG z lepszym ad copy"
        return "Popraw nagłówki reklam — dodaj słowo kluczowe w Headline 1 + CTA"
    elif primary == "ad_relevance":
        if is_lost > 0.2:
            return f"Trafność poniżej śr. + {is_lost*100:.0f}% IS lost — dopasuj tekst reklamy, rozważ DKI"
        return "Popraw trafność — keyword w nagłówku + opis dopasowany do intencji"
    elif primary == "landing_page":
        if cost > 50 and convs == 0:
            return f"LP poniżej śr. + {cost:.0f} zł bez konwersji — sprawdź szybkość LP, CTA above the fold"
        return "Popraw stronę docelową — szybkość < 3s, keyword w H1, wyraźne CTA"

    return "Sprawdź dopasowanie reklamy do słowa kluczowego"
