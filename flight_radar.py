from discord.ext import commands, tasks
from datetime import datetime, time
import pytz
from amadeus import Client, ResponseError
import os
import discord

class FlightCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.amadeus = Client(
            client_id=os.environ["AMADEUS_API_KEY"],
            client_secret=os.environ["AMADEUS_API_SECRET"]
        )
        self.check_flights.start()

    def cog_unload(self):
        self.check_flights.cancel()

    async def get_cheap_flights(self):
        try:
            chile_tz = pytz.timezone('America/Santiago')
            today = datetime.now(chile_tz).strftime('%Y-%m-%d')
            
            response = self.amadeus.shopping.flight_offers_search.get(
                originLocationCode=os.environ["SANTIAGO_IATA"],
                destinationLocationCode=os.environ["TOKYO_IATA"],
                departureDate=today,
                adults=1,
                max=10
            )
            
            flights = []
            for offer in response.data:
                price = float(offer['price']['total'])
                departure = offer['itineraries'][0]['segments'][0]['departure']['at']
                arrival = offer['itineraries'][0]['segments'][-1]['arrival']['at']
                
                flights.append({
                    'price': price,
                    'departure': departure,
                    'arrival': arrival,
                    'duration': offer['itineraries'][0]['duration']
                })
            
            flights.sort(key=lambda x: x['price'])
            return flights[:10]
            
        except ResponseError as error:
            print(f"Error al buscar vuelos: {error}")
            return None

    @tasks.loop(time=time(hour=13, minute=0, tzinfo=pytz.timezone('America/Santiago')))
    async def check_flights(self):
        channel = discord.utils.get(self.bot.get_all_channels(), name=os.environ["CHANNEL_NAME"])
        if not channel:
            print(f"No se encontró el canal {os.environ['CHANNEL_NAME']}")
            return

        flights = await self.get_cheap_flights()
        if not flights:
            await channel.send("❌ No se pudieron obtener los vuelos en este momento.")
            return

        embed = discord.Embed(
            title="🛫 Top 10 Vuelos más Baratos a Japón",
            description="Saliendo desde Santiago de Chile",
            color=discord.Color.blue()
        )
        
        for i, flight in enumerate(flights, 1):
            departure_time = datetime.fromisoformat(flight['departure'].replace('Z', '+00:00'))
            arrival_time = datetime.fromisoformat(flight['arrival'].replace('Z', '+00:00'))
            
            embed.add_field(
                name=f"#{i} - ${flight['price']:,.0f} USD",
                value=f"🛫 Salida: {departure_time.strftime('%Y-%m-%d %H:%M')}\n"
                      f"🛬 Llegada: {arrival_time.strftime('%Y-%m-%d %H:%M')}\n"
                      f"⏱️ Duración: {flight['duration']}",
                inline=False
            )

        await channel.send(embed=embed)

    @check_flights.before_loop
    async def before_check_flights(self):
        await self.bot.wait_until_ready()

    @commands.command()
    async def check_flights_now(self, ctx):
        """Comando manual para verificar vuelos inmediatamente"""
        await self.check_flights()

async def setup(bot):
    await bot.add_cog(FlightCog(bot))