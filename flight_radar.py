from discord.ext import commands, tasks
from datetime import datetime, time
import pytz
from amadeus import Client, ResponseError
import os
import discord
import urllib.parse

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

    def create_google_flights_link(self, departure_date, from_code="SCL", to_code="NRT"):
        """Crea un link a Google Flights con los parámetros del vuelo"""
        base_url = "https://www.google.com/travel/flights"
        params = {
            "hl": "es",  # idioma español
            "curr": "USD",  # moneda en USD
            "tfs": "1",  # búsqueda de vuelos
            "q": f"flights from {from_code} to {to_code}",
            "d": departure_date.strftime("%Y-%m-%d")  # fecha en formato YYYY-MM-DD
        }
        return f"{base_url}?{urllib.parse.urlencode(params)}"

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
                
                # Obtener detalles de los vuelos
                flight_numbers = [
                    f"{segment['carrierCode']}{segment['number']}"
                    for segment in offer['itineraries'][0]['segments']
                ]
                
                flights.append({
                    'price': price,
                    'departure': departure,
                    'arrival': arrival,
                    'duration': offer['itineraries'][0]['duration'],
                    'carriers': [segment['carrierCode'] for segment in offer['itineraries'][0]['segments']],
                    'flight_numbers': flight_numbers
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
            
            # Crear el link a Google Flights
            flight_link = self.create_google_flights_link(departure_time)
            
            # Crear una lista de aerolíneas y códigos de vuelo
            airlines = ', '.join(flight['carriers'])
            flight_numbers = ', '.join(flight['flight_numbers'])
            
            embed.add_field(
                name=f"#{i} - ${flight['price']:,.0f} USD",
                value=f"🛫 Salida: {departure_time.strftime('%Y-%m-%d %H:%M')}\n"
                      f"🛬 Llegada: {arrival_time.strftime('%Y-%m-%d %H:%M')}\n"
                      f"✈️ Aerolíneas: {airlines}\n"
                      f"🔢 Código de vuelo: {flight_numbers}\n"
                      f"⏱️ Duración: {flight['duration']}\n"
                      f"🔍 [Ver en Google Flights]({flight_link})",
                inline=False
            )

        embed.set_footer(text="Los precios pueden variar. Haz clic en 'Ver en Google Flights' para verificar la disponibilidad actual.")
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
