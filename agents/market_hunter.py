from app.providers import ai_provider
class MarketHunter:
    def run(self, product):
        countries=product.get('target_countries') or []
        markets=[{'country':c,'status':'research_required'} for c in countries]
        if countries:
            analysis=ai_provider.analyze('market_hunter',{'product':product,'countries':countries})
            for m in markets:m['ai_research']=analysis
        return markets
