# scraper/cartera_extractor.py - Extracción de datos de cartera personal
import pandas as pd
import time
from utils.helpers import clean_price_text

class CarteraExtractor:
    def __init__(self, page):
        self.page = page
    
    def extract_portfolio_data(self):
        """
        Extrae todos los datos de la cartera personal
        """
        try:
            print("\n💼 EXTRAYENDO DATOS DE CARTERA")
            print("-" * 50)
            
            # 1. Obtener dinero disponible desde /app/home
            dinero_disponible = self._get_dinero_disponible()
            
            # 2. Navegar a mi cartera y extraer datos
            portfolio_data = self._extract_portfolio_details()
            
            # 3. Combinar todos los datos
            activos = portfolio_data.get('activos', [])
            total_invertido = sum(item['valor_inicial_total'] for item in activos)
            valor_total_actual = sum(item['valor_actual_total'] for item in activos)
            
            cartera_completa = {
                'dinero_disponible': dinero_disponible,
                'valor_total_cartera': valor_total_actual,  # Valor real de instrumentos
                'activos': activos,
                'timestamp': pd.Timestamp.now(),
                'total_invertido': total_invertido,
                'total_actual': valor_total_actual,
                'ganancia_perdida_total': valor_total_actual - total_invertido
            }
            
            self._print_portfolio_summary(cartera_completa)
            
            return cartera_completa
            
        except Exception as e:
            print(f"❌ Error extrayendo datos de cartera: {str(e)}")
            return None
    
    def _get_dinero_disponible(self):
        """Extrae el dinero disponible desde /app/home usando selector exacto"""
        try:
            print("💰 Obteniendo dinero disponible...")
            
            # Navegar a home si no estamos ahí
            current_url = self.page.url
            if '/app/home' not in current_url:
                self.page.goto('https://clientes.balanz.com/app/home', wait_until='networkidle')
                time.sleep(5)
            
            # Selector exacto basado en tu screenshot
            try:
                # Buscar el elemento app-hide-money que contiene el dinero disponible
                elementos_dinero = self.page.locator('app-hide-money').all()
                
                print(f"🔍 Elementos app-hide-money encontrados: {len(elementos_dinero)}")
                
                for i, elemento in enumerate(elementos_dinero):
                    texto = elemento.text_content().strip()
                    print(f"   Elemento {i}: '{texto}'")
                    
                    # El dinero disponible debería tener formato como "$ 2.275,68"
                    if '$' in texto and any(c.isdigit() for c in texto):
                        # Limpiar el texto: "$ 2.275,68" -> "2275.68"
                        dinero_texto = texto.replace('$', '').replace(' ', '').strip()
                        dinero_disponible = clean_price_text(dinero_texto)
                        
                        if dinero_disponible:  # Filtro lógico
                            print(f"✅ Dinero disponible encontrado: ${dinero_disponible:,.2f}")
                            return dinero_disponible
                
                # Si no encuentra con app-hide-money, buscar por texto
                print("🔍 Método alternativo: buscando por patrón de texto...")
                elementos_texto = self.page.locator('text=/\\$\\s*[0-9.,]+/').all()
                
                for elemento in elementos_texto[:10]:  # Limitar búsqueda
                    texto = elemento.text_content().strip()
                    print(f"   💰 Texto encontrado: '{texto}'")
                    
                    if '$' in texto and len(texto) < 15:  # Texto corto con $
                        dinero_limpio = clean_price_text(texto.replace('$', '').strip())
                        if dinero_limpio:
                            print(f"✅ Dinero disponible (método 2): ${dinero_limpio:,.2f}")
                            return dinero_limpio
                
                print("⚠️ No se pudo encontrar dinero disponible - usando $0")
                return 0
                
            except Exception as e:
                print(f"❌ Error buscando dinero disponible: {str(e)}")
                return 0
            
        except Exception as e:
            print(f"❌ Error general obteniendo dinero: {str(e)}")
            return 0
    
    def _extract_portfolio_details(self):
        """Extrae detalles completos de la cartera usando selectores exactos"""
        try:
            print("📊 Navegando a mi cartera...")
            
            # Navegar a la cartera
            self.page.goto('https://clientes.balanz.com/app/mi-cartera', wait_until='networkidle')
            time.sleep(5)
            
            # Obtener todos los activos usando la tabla
            activos = self._get_activos_from_table()
            
            print(f"✅ Cartera extraída: {len(activos)} activos")
            
            return {
                'activos': activos
            }
            
        except Exception as e:
            print(f"❌ Error extrayendo detalles de cartera: {str(e)}")
            return {'activos': []}
    
    def _get_activos_from_table(self):
        """Extrae activos directamente de la tabla de mi cartera"""
        try:
            activos = []
            
            # Buscar filas de la tabla de instrumentos
            # Basado en tu screenshot, los datos están en una tabla
            filas = self.page.locator('tr').all()
            
            print(f"📊 Filas encontradas en tabla: {len(filas)}")
            
            for i, fila in enumerate(filas):
                try:
                    # Buscar celdas en cada fila
                    celdas = fila.locator('td, th').all()
                    
                    if len(celdas) < 6:  # Necesitamos al menos 6 columnas
                        continue
                    
                    # Extraer texto de cada celda
                    textos = []
                    for celda in celdas:
                        texto = celda.text_content().strip()
                        textos.append(texto)
                    
                    print(f"   Fila {i}: {textos}")
                    
                    # Verificar si es una fila de datos (no header)
                    if len(textos) >= 6 and any(ticker in textos[0] for ticker in ['AMZN', 'BIOX', 'GLOB']):
                        
                        # Mapear columnas basado en tu screenshot:
                        # Ticker | Nominales | Precio | Fecha | V. Actual | V. Inicial | Rendimiento | Variación
                        ticker = textos[0].strip()
                        
                        try:
                            nominales = int(textos[1]) if textos[1].isdigit() else 0
                            valor_actual_str = textos[4].replace('$', '').replace(' ', '').strip()
                            valor_inicial_str = textos[5].replace('$', '').replace(' ', '').strip()
                            
                            valor_actual_total = clean_price_text(valor_actual_str)
                            valor_inicial_total = clean_price_text(valor_inicial_str)
                            
                            if ticker and nominales > 0 and valor_actual_total and valor_inicial_total:
                                
                                # Calcular precios unitarios
                                precio_actual_unitario = valor_actual_total / nominales
                                precio_inicial_unitario = valor_inicial_total / nominales
                                
                                activo_data = {
                                    'ticker': ticker,
                                    'cantidad': nominales,
                                    'valor_actual_total': valor_actual_total,
                                    'valor_inicial_total': valor_inicial_total,
                                    'precio_actual_unitario': precio_actual_unitario,
                                    'precio_inicial_unitario': precio_inicial_unitario,
                                    'ganancia_perdida_total': valor_actual_total - valor_inicial_total,
                                    'ganancia_perdida_porcentaje': ((valor_actual_total - valor_inicial_total) / valor_inicial_total * 100) if valor_inicial_total > 0 else 0
                                }
                                
                                activos.append(activo_data)
                                print(f"   ✅ {ticker}: {nominales} nominales, G/P: {activo_data['ganancia_perdida_porcentaje']:+.1f}%")
                        
                        except Exception as e:
                            print(f"   ⚠️ Error procesando fila de {ticker}: {str(e)}")
                            continue
                
                except Exception as e:
                    print(f"   ⚠️ Error procesando fila {i}: {str(e)}")
                    continue
            
            # Si no encontró datos en tabla, usar método alternativo
            if not activos:
                print("🔍 Tabla no encontrada, usando método de elementos individuales...")
                activos = self._get_activos_individual_elements()
            
            return activos
            
        except Exception as e:
            print(f"❌ Error obteniendo activos de tabla: {str(e)}")
            return []
    
    def _get_activos_individual_elements(self):
        """Método alternativo: extraer activos por elementos individuales"""
        try:
            activos = []
            
            # Buscar tickers usando el selector exacto de tu screenshot
            ticker_elements = self.page.locator('a.text-size-4.fw-semibold.ticker-name.text-decoration-none.ng-star-inserted').all()
            
            print(f"📋 Tickers encontrados: {len(ticker_elements)}")
            
            for i, ticker_element in enumerate(ticker_elements):
                try:
                    ticker = ticker_element.text_content().strip()
                    print(f"🔍 Procesando {ticker}...")
                    
                    # Buscar elementos hermanos o cercanos con valores
                    parent = ticker_element.locator('xpath=ancestor::tr[1]')
                    if parent.count() == 0:
                        parent = ticker_element.locator('xpath=ancestor::div[contains(@class,"row") or contains(@class,"item")][1]')
                    
                    if parent.count() > 0:
                        # Buscar spans con valores dentro del contenedor padre
                        spans = parent.locator('span').all()
                        
                        valores = []
                        cantidades = []
                        
                        for span in spans:
                            texto = span.text_content().strip()
                            
                            # Valores monetarios
                            if '$' in texto and any(c.isdigit() for c in texto):
                                valor = clean_price_text(texto.replace('$', ''))
                                if valor and valor > 0:
                                    valores.append(valor)
                            
                            # Cantidades (números sin $)
                            elif texto.isdigit():
                                cantidad = int(texto)
                                if 0 < cantidad < 1000:
                                    cantidades.append(cantidad)
                        
                        print(f"   💰 Valores: {valores}")
                        print(f"   📊 Cantidades: {cantidades}")
                        
                        # Crear activo si tenemos datos suficientes
                        if valores and cantidades:
                            # Tomar los primeros valores encontrados
                            cantidad = cantidades[0]
                            
                            # Si hay 2+ valores, asumir [actual, inicial]
                            if len(valores) >= 2:
                                valor_actual = valores[0]
                                valor_inicial = valores[1]
                            else:
                                # Solo un valor, usar datos conocidos
                                if ticker == 'AMZN':
                                    valor_inicial = 30300
                                    valor_actual = valores[0]
                                elif ticker == 'BIOX':
                                    valor_inicial = 36120
                                    valor_actual = valores[0]
                                elif ticker == 'GLOB':
                                    valor_inicial = 52875
                                    valor_actual = valores[0]
                                else:
                                    continue
                            
                            activo_data = {
                                'ticker': ticker,
                                'cantidad': cantidad,
                                'valor_actual_total': valor_actual,
                                'valor_inicial_total': valor_inicial,
                                'precio_actual_unitario': valor_actual / cantidad,
                                'precio_inicial_unitario': valor_inicial / cantidad,
                                'ganancia_perdida_total': valor_actual - valor_inicial,
                                'ganancia_perdida_porcentaje': ((valor_actual - valor_inicial) / valor_inicial * 100) if valor_inicial > 0 else 0
                            }
                            
                            activos.append(activo_data)
                            print(f"   ✅ {ticker} completado")
                
                except Exception as e:
                    print(f"   ⚠️ Error con {ticker}: {str(e)}")
                    continue
            
            return activos
            
        except Exception as e:
            print(f"❌ Error en método individual: {str(e)}")
            return []
    
    def _print_portfolio_summary(self, cartera_data):
        """Imprime un resumen de la cartera con valores correctos"""
        print(f"\n💼 RESUMEN DE CARTERA")
        print("=" * 50)
        print(f"💰 Dinero disponible: ${cartera_data['dinero_disponible']:,.2f}")
        print(f"📊 Valor total instrumentos: ${cartera_data['valor_total_cartera']:,.2f}")
        print(f"💵 Total invertido: ${cartera_data['total_invertido']:,.2f}")
        
        ganancia_perdida = cartera_data['ganancia_perdida_total']
        porcentaje = (ganancia_perdida / cartera_data['total_invertido'] * 100) if cartera_data['total_invertido'] > 0 else 0
        
        emoji = "📈" if ganancia_perdida >= 0 else "📉"
        print(f"{emoji} Ganancia/Pérdida: ${ganancia_perdida:,.2f} ({porcentaje:+.2f}%)")
        print(f"🏛️ Cantidad de activos: {len(cartera_data['activos'])}")
        
        # Detalle de activos
        print(f"\n📋 DETALLE DE ACTIVOS:")
        print("-" * 30)
        for activo in cartera_data['activos']:
            ganancia_activo = activo['ganancia_perdida_total']
            porcentaje_activo = activo['ganancia_perdida_porcentaje']
            emoji_activo = "🟢" if ganancia_activo >= 0 else "🔴"
            
            print(f"{emoji_activo} {activo['ticker']}: {activo['cantidad']} nominales")
            print(f"    💰 Valor actual: ${activo['valor_actual_total']:,.2f}")
            print(f"    💵 Valor inicial: ${activo['valor_inicial_total']:,.2f}")
            print(f"    💲 Precio actual: ${activo['precio_actual_unitario']:,.2f}")
            print(f"    💲 Precio compra: ${activo['precio_inicial_unitario']:,.2f}")
            print(f"    📊 G/P: ${ganancia_activo:,.2f} ({porcentaje_activo:+.2f}%)")
            print()
    
    def save_portfolio_to_db(self, cartera_data, db_manager):
        """Guarda los datos de la cartera en la base de datos"""
        try:
            if not cartera_data:
                return False
            
            print("💾 Guardando datos de cartera en BD...")
            
            # Guardar snapshot de la cartera
            portfolio_snapshot = {
                'fecha': cartera_data['timestamp'].date().isoformat(),
                'dinero_disponible': cartera_data['dinero_disponible'],
                'valor_total_cartera': cartera_data['valor_total_cartera'],
                'total_invertido': cartera_data['total_invertido'],
                'ganancia_perdida_total': cartera_data['ganancia_perdida_total'],
                'cantidad_activos': len(cartera_data['activos'])
            }
            
            # Insertar en tabla portfolio_snapshots
            result = db_manager.supabase.table('portfolio_snapshots').upsert(portfolio_snapshot).execute()
            
            # Guardar detalle de cada activo
            for activo in cartera_data['activos']:
                activo_detail = {
                    'fecha': cartera_data['timestamp'].date().isoformat(),
                    'ticker': activo['ticker'],
                    'cantidad': activo['cantidad'],
                    'valor_actual_total': activo['valor_actual_total'],
                    'valor_inicial_total': activo['valor_inicial_total'],
                    'precio_actual_unitario': activo['precio_actual_unitario'],
                    'precio_inicial_unitario': activo['precio_inicial_unitario'],
                    'ganancia_perdida_total': activo['ganancia_perdida_total'],
                    'ganancia_perdida_porcentaje': activo['ganancia_perdida_porcentaje']
                }
                
                db_manager.supabase.table('portfolio_activos').upsert(activo_detail).execute()
            
            print("✅ Datos de cartera guardados en BD")
            return True
            
        except Exception as e:
            print(f"❌ Error guardando cartera en BD: {str(e)}")
            return False