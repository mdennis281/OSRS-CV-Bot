from bots.motherload_miner import BotConfig, BotExecutor


def main():
    config = BotConfig()
    bot = BotExecutor(config)
    
    bot.start()
    
main()