package com.ibm.websphere.samples.daytrader.web;

import com.ibm.websphere.samples.daytrader.entities.QuoteDataBean;
import com.ibm.websphere.samples.daytrader.interfaces.TradeServices;
import java.util.ArrayList;
import java.util.List;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** The stock quote API shared with the Jakarta and Quarkus DayTrader applications. */
@RestController
@RequestMapping("/rest/quotes")
public class QuoteController {

    private final TradeServices tradeServices;

    public QuoteController(@Qualifier("Direct (JDBC)") TradeServices tradeServices) {
        this.tradeServices = tradeServices;
    }

    @GetMapping(value = "/{symbols}", produces = MediaType.APPLICATION_JSON_VALUE)
    public List<QuoteDataBean> getQuotes(@PathVariable String symbols) throws Exception {
        List<QuoteDataBean> quotes = new ArrayList<>();
        for (String symbol : symbols.split(",")) {
            QuoteDataBean quote = tradeServices.getQuote(symbol.trim());
            if (quote != null) {
                quotes.add(quote);
            }
        }
        return quotes;
    }

    @PostMapping(consumes = MediaType.APPLICATION_FORM_URLENCODED_VALUE,
            produces = MediaType.APPLICATION_JSON_VALUE)
    public List<QuoteDataBean> postQuotes(@RequestParam String symbols) throws Exception {
        return getQuotes(symbols);
    }
}
