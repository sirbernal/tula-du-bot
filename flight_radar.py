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

    def create_google_flights_link(self, from_code, to_code, departure_date, return_date=None):
        """Crea un enlace optimizado a Google Flights con los parámetros del vuelo específico."""
        base_url = "https://www.google.com/flights"
        departure_str = f"{departure_date.strftime('%Y-%m-%d')}"

        # Agrega la fecha de retorno si está disponible
        if return_date:
            return_str = f"{return_date.strftime('%Y-%m-%d')}"
        else:
            return_str = ""

        # El formato de URL específico para Google Flights
        return f"{base_url}?hl=es&gl=us&curr=USD#flt={from_code}.{to_code}.{departure_str};c:USD;e:1;sd:1;t:f{':' + return_str if return_str else ''}"


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
            
            # Crear el link a Google Flights específico
            flight_link = self.create_google_flights_link(
                from_code=os.environ["SANTIAGO_IATA"],
                to_code=os.environ["TOKYO_IATA"],
                departure_date=departure_time
            )
            
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
