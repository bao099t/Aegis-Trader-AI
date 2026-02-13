import requests
import os
import datetime

class DiscordWebhook:
    def __init__(self):
        # Load from Environment variable for security
        self.url = os.getenv("DISCORD_WEBHOOK_URL", "")
        if not self.url:
             print("  ⚠️ [Discord] No Webhook URL found in environment (DISCORD_WEBHOOK_URL). Alerts will fail.")
        
    def send_alert(self, news_item):
        analysis = news_item.get('analysis', {})
        market = analysis.get('market_analysis', {})
        
        # Color Logic
        color = 0x808080 # Grey (Neutral)
        direction = market.get('direction', 'NEUTRAL')
        
        if direction == "BULLISH":
            color = 0x00FF00 # Green
        elif direction == "BEARISH":
            color = 0xFF0000 # Red
        elif direction == "VOLATILE":
            color = 0xFFA500 # Orange
            
        # Title Prefix
        emoji = "⚪"
        if direction == "BULLISH": emoji = "🚀"
        if direction == "BEARISH": emoji = "WARNING ⚠️"
        
        # Sniper/Watchlist Highlight
        if analysis.get('is_watchlist'):
            emoji = "🎯 " + emoji + " [SNIPER]"
            color = 0xFFD700 # Gold color for Watchlist
        
        clean_title = news_item['title']
        
        # Fundamentals Context
        context_str = ""
        ctx = market.get('context')
        if ctx:
            pe = ctx.get('pe_ratio', 'N/A')
            mc = ctx.get('market_cap_fmt', 'N/A')
            sector = ctx.get('sector', 'Unknown')
            context_str = f"**Sector:** {sector}\n**Mkt Cap:** {mc} | **P/E:** {pe}"
            
        # Construct Embed field
        description = f"**Source**: {news_item['source']}\n"
        if market.get('reason'):
            description += f"**Analysis**: {market['reason']}\n"
        
        if context_str:
            description += f"\n{context_str}"
            
        # Technicals
        tech = market.get('technical')
        if tech:
            rsi = tech.get('rsi', 'N/A')
            state = tech.get('rsi_state', 'NEUTRAL')
            trend = tech.get('trend', 'NEUTRAL')
            
            # Icons
            t_icon = "⚪"
            if trend == "UPTREND": t_icon = "📈"
            if trend == "DOWNTREND": t_icon = "📉"
            
            description += f"\n**Technicals**: RSI: {rsi} ({state}) | Trend: {t_icon} {trend}"
            
        # Macro Warning
        macro = market.get('macro')
        if macro:
            vix = macro.get('vix', 0)
            mood = macro.get('mood', 'NORMAL')
            if macro.get('risk_status') == "RISK-OFF":
                description += f"\n\n🌪️ **MARKET STORM WARNING** 🌪️\n**VIX**: {vix} ({mood})\n*Trade with caution.*"
                
        # Institutional Audit
        inst = market.get('institutional')
        if inst:
            vol = inst['volume']['msg']
            rs = inst['relative_strength']['msg']
            sec = inst['sector']['msg']
            
            
            description += f"\n\n**🏥 INSTITUTIONAL AUDIT**\n- {vol}\n- {rs}\n- {sec}"
            
        # Psychological Audit
        psych = market.get('psychology')
        if psych:
            sat = psych['saturation']['msg']
            gap = psych['gap_risk']['msg']
            div = psych['divergence']['msg']
            
            description += f"\n\n**🧠 BEHAVIORAL AUDIT**\n- {sat}\n- {gap}\n- {div}"

        # Final Synthesis (Phase 18)
        synth = market.get('synthesis')
        if synth:
            score = synth['score']
            verdict = synth['verdict']
            
            # Simple bar [||||------]
            bar_count = int(score / 10)
            bar = "█" * bar_count + "░" * (10 - bar_count)
            
            size = synth.get('suggested_size', 'N/A')
            sl = synth.get('stop_loss')
            sl_fmt = f"${sl:.2f}" if sl else "N/A"
            
            description += f"\n\n**🏁 FINAL SYNTHESIS**\n`[{bar}] {score}%` \n**Verdict**: {verdict}\n**Trade Guidance**: Use **{size}** | SL: **{sl_fmt}**"

        # Deception Warning (Phase 21)
        if market.get('is_verified') == False:
            description += f"\n\n⚠️ **DECEPTION WARNING** ⚠️\n*Sentiment vs Reality Divergence detected. This ticker is fighting its own trend.*"

        description += f"\n[Read Article]({news_item['link']})"

        payload = {
            "username": "Market Mind AI",
            "embeds": [
                {
                    "title": f"{emoji} {direction}: {clean_title}",
                    "description": description,
                    "color": color,
                    "footer": {
                        "text": f"AI Confidence (Sentiment): {analysis.get('sentiment', 0):.2f}"
                    },
                    "timestamp": news_item.get('published')
                }
            ]
        }
        
        try:
            requests.post(self.url, json=payload)
        except Exception as e:
            print(f"Failed to send Discord alert: {e}")

    def send_heartbeat(self, stats):
        """
        Sends a periodic status update to keep users engaged.
        stats = {
            'scanned_count': int,
            'guardian_status': str,
            'market_mood': str
        }
        """
        scanned = stats.get('scanned_count', 0)
        status = stats.get('guardian_status', 'ACTIVE')
        mood = stats.get('market_mood', 'NEUTRAL')
        
        color = 0x00BFFF # Deep Sky Blue
        emoji = "🛡️"
        if status != "ACTIVE": 
            color = 0xFFA500 # Orange
            emoji = "⚠️"
            
        description = (
            f"**System Status**: {emoji} {status}\n"
            f"**Activity (Last Hour)**: Scanned **{scanned}** potential setups.\n"
            f"**Market Mood**: {mood}\n\n"
            "*\"No trade is better than a bad trade. Searching for Elite setups...\"*"
        )
        
        payload = {
            "username": "Market Mind AI (Heartbeat)",
            "embeds": [{
                "title": "💓 Market Heartbeat",
                "description": description,
                "color": color,
                "footer": {"text": "Bot is Alive & Hunting"},
                "timestamp": datetime.datetime.utcnow().isoformat()
            }]
        }
        
        try:
            requests.post(self.url, json=payload)
        except Exception as e:
            print(f"Failed to send Heartbeat: {e}")


# Module-level wrapper for easier import
def send_alert(news_item):
    webhook = DiscordWebhook()
    webhook.send_alert(news_item)

def send_heartbeat(stats):
    webhook = DiscordWebhook()
    webhook.send_heartbeat(stats)
