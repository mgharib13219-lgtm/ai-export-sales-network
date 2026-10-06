class NegotiationAgent:
    '''Evaluate buyer counteroffers without accepting them.'''
    def evaluate_counteroffer(self, quote, counter_unit_price, max_discount_pct=5.0):
        if counter_unit_price is None or float(counter_unit_price) <= 0:
            return {'status':'invalid_counteroffer'}
        target=float(quote.get('commercials',{}).get('indicative_buyer_price',0))
        if target <= 0:
            return {'status':'missing_quote_target'}
        counter=float(counter_unit_price)
        variance_pct=(counter-target)/target*100
        acceptable_floor=target*(1-float(max_discount_pct)/100)
        within_bounds=counter >= acceptable_floor
        return {
            'status':'review_required',
            'decision':'human_review_required',
            'target_price':round(target,6),
            'counter_unit_price':round(counter,6),
            'variance_pct':round(variance_pct,4),
            'acceptable_floor':round(acceptable_floor,6),
            'within_approval_bounds':within_bounds,
            'recommendation':'counter_or_accept_after_human_review' if within_bounds else 'escalate_for_human_review',
            'never_auto_accept':True,
        }
