# scraper/cartera_extractor.py - Corregido para detectar cualquier activo
import pandas as pd
import time
from utils.helpers import clean_price_text

class CarteraExtractor:
    def __init__(self, page):
        self.page = page
    
    def extract_portfolio_data(self):
        """Extrae todos los datos de la cartera personal"""
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
                'valor_total_cartera': valor_total_actual,
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
        """Extrae el dinero disponible desde /app/home"""
        try:
            print("💰 Obteniendo dinero disponible...")
            
            # Navegar a home si no estamos ahí
            current_url = self.page.url
            if '/app/home' not in current_url:
                self.page.goto('https://clientes.balanz.com/app/home', wait_until='networkidle')
                time.sleep(5)
            
            try:
                elementos_dinero = self.page.locator('app-hide-money').all()
                
                print(f"🔍 Elementos app-hide-money encontrados: {len(elementos_dinero)}")
                
                for i, elemento in enumerate(elementos_dinero):
                    texto = elemento.text_content().strip()
                    print(f"   Elemento {i}: '{texto}'")
                    
                    if '$' in texto and any(c.isdigit() for c in texto):
                        dinero_texto = texto.replace('$', '').replace(' ', '').strip()
                        dinero_disponible = clean_price_text(dinero_texto)
                        
                        if dinero_disponible is not None:
                            print(f"✅ Dinero disponible encontrado: ${dinero_disponible:,.2f}")
                            return dinero_disponible
                
                print("⚠️ No se pudo encontrar dinero disponible - usando $0")
                return 0
                
            except Exception as e:
                print(f"❌ Error buscando dinero disponible: {str(e)}")
                return 0
            
        except Exception as e:
            print(f"❌ Error general obteniendo dinero: {str(e)}")
            return 0
    
    def _extract_portfolio_details(self):
        """Extrae detalles completos de la cartera SIN restricciones de tickers"""
        try:
            print("📊 Navegando a mi cartera...")
            
            # Navegar a la cartera
            self.page.goto('https://clientes.balanz.com/app/mi-cartera', wait_until='networkidle')
            time.sleep(5)
            
            # Obtener todos los activos usando la tabla
            activos = self._get_activos_from_table()
            
            print(f"✅ Cartera extraída: {len(activos)} activos")
            
            return {'activos': activos}
            
        except Exception as e:
            print(f"❌ Error extrayendo detalles de cartera: {str(e)}")
            return {'activos': []}
    
    def _get_activos_from_table(self):
        """Extrae activos SIN lista hardcodeada - detecta cualquier ticker válido"""
        try:
            activos = []
            
            # Usar método genérico directo
            filas = self.page.locator('tr').all()
            
            print(f"📊 Filas totales encontradas: {len(filas)}")
            
            for i, fila in enumerate(filas):
                try:
                    # Buscar celdas en cada fila
                    celdas = fila.locator('td, th').all()
                    
                    if len(celdas) < 8:
                        continue
                    
                    # Extraer texto de cada celda
                    textos = []
                    for celda in celdas:
                        texto = celda.text_content().strip()
                        textos.append(texto)
                    
                    print(f"   Fila {i}: {textos}")
                    
                    # LÓGICA CORREGIDA: Detectar filas válidas sin lista hardcodeada
                    es_fila_datos = self._is_valid_ticker_row(textos)
                    
                    if es_fila_datos:
                        ticker = textos[0].strip()
                        
                        try:
                            nominales = int(textos[1]) if textos[1].isdigit() else 0
                            
                            # Limpiar valores monetarios
                            valor_actual_str = textos[4].replace('$', '').replace(' ', '').strip()
                            valor_inicial_str = textos[5].replace('$', '').replace(' ', '').strip()
                            
                            valor_actual_total = clean_price_text(valor_actual_str)
                            valor_inicial_total = clean_price_text(valor_inicial_str)
                            
                            # Extraer días de tenencia
                            dias_tenencia = self._extract_days_from_row(fila, ticker, textos)
                            
                            print(f"   📊 Procesando: {ticker} - Nominales: {nominales} - DPT: {dias_tenencia}")
                            
                            if ticker and nominales > 0 and valor_actual_total and valor_inicial_total:
                                
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
                                    'ganancia_perdida_porcentaje': ((valor_actual_total - valor_inicial_total) / valor_inicial_total * 100) if valor_inicial_total > 0 else 0,
                                    'dias_tenencia': dias_tenencia
                                }
                                
                                activos.append(activo_data)
                                print(f"   ✅ {ticker}: {nominales} nominales, {dias_tenencia} días, G/P: {activo_data['ganancia_perdida_porcentaje']:+.1f}%")
                        
                        except Exception as e:
                            print(f"   ⚠️ Error procesando fila de {ticker}: {str(e)}")
                            continue
                
                except Exception as e:
                    print(f"   ⚠️ Error procesando fila {i}: {str(e)}")
                    continue
            
            return activos
            
        except Exception as e:
            print(f"❌ Error obteniendo activos de tabla: {str(e)}")
            return []
    
    def _is_valid_ticker_row(self, textos):
        """Determina si una fila contiene datos válidos de un ticker SIN lista hardcodeada"""
        if len(textos) < 8:
            return False
        
        ticker = textos[0].strip()
        nominales = textos[1].strip()
        precio = textos[2].strip()
        valor_actual = textos[4].strip()
        valor_inicial = textos[5].strip()
        
        # Criterios para identificar fila válida:
        return (
            # 1. Ticker no es header ni total
            ticker not in ['Ticker', 'Totales', ''] and
            len(ticker) >= 2 and len(ticker) <= 6 and  # Longitud típica de ticker
            ticker.isalpha() or any(c.isdigit() for c in ticker) and  # Solo letras o alphanúmerico
            
            # 2. Nominales es número
            nominales.isdigit() and int(nominales) > 0 and
            
            # 3. Precio tiene formato monetario
            '$' in precio and
            
            # 4. Valores actuales e iniciales tienen formato monetario
            '$' in valor_actual and '$' in valor_inicial
        )
    
    def _extract_days_from_row(self, fila, ticker, textos):
        """Extrae días de tenencia usando múltiples métodos"""
        try:
            print(f"🔍 Extrayendo días de tenencia para {ticker}...")
            
            # MÉTODO 1: Buscar en las celdas por posición (si hay 9 columnas)
            if len(textos) >= 9 and textos[8].isdigit():
                dias = int(textos[8])
                print(f"   ✅ Días desde posición 8: {dias}")
                return dias
            
            # MÉTODO 2: Buscar spans con contenido numérico que no sea nominales ni precios
            try:
                spans = fila.locator('span').all()
                for span in spans:
                    texto = span.text_content().strip()
                    if texto.isdigit():
                        numero = int(texto)
                        # Filtrar valores que claramente no son días
                        if 1 <= numero <= 9999 and texto != textos[1]:  # No es nominales
                            # Verificar que no sea parte de un precio
                            parent_text = span.locator('xpath=..').text_content()
                            if '$' not in parent_text and ',' not in parent_text:
                                dias = numero
                                print(f"   ✅ Días desde span: {dias}")
                                return dias
            except Exception as e:
                print(f"   ⚠️ Método 2 falló: {str(e)}")
            
            # MÉTODO 3: Buscar usando selector específico para DPT
            try:
                dpt_cells = fila.locator('td.text-size-4.ng-star-inserted').all()
                for cell in dpt_cells:
                    spans_in_cell = cell.locator('span').all()
                    for span in spans_in_cell:
                        texto = span.text_content().strip()
                        if texto.isdigit() and 1 <= int(texto) <= 999:
                            if texto != textos[1]:  # No es nominales
                                dias = int(texto)
                                print(f"   ✅ Días desde método 3: {dias}")
                                return dias
            except Exception as e:
                print(f"   ⚠️ Método 3 falló: {str(e)}")
            
            print(f"   ⚠️ No se encontraron días para {ticker} - usando 1")
            return 1  # Default
            
        except Exception as e:
            print(f"⚠️ Error extrayendo días de {ticker}: {str(e)}")
            return 1
    
    def _print_portfolio_summary(self, cartera_data):
        """Imprime un resumen de la cartera"""
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
            dias_tenencia = activo.get('dias_tenencia', 0)
            emoji_activo = "🟢" if ganancia_activo >= 0 else "🔴"
            
            # Calcular rendimiento anualizado
            if dias_tenencia > 0:
                rendimiento_anualizado = (porcentaje_activo / dias_tenencia) * 365
            else:
                rendimiento_anualizado = 0
            
            print(f"{emoji_activo} {activo['ticker']}: {activo['cantidad']} nominales")
            print(f"    💰 Valor actual: ${activo['valor_actual_total']:,.2f}")
            print(f"    💵 Valor inicial: ${activo['valor_inicial_total']:,.2f}")
            print(f"    💲 Precio actual: ${activo['precio_actual_unitario']:,.2f}")
            print(f"    💲 Precio compra: ${activo['precio_inicial_unitario']:,.2f}")
            print(f"    📊 G/P: ${ganancia_activo:,.2f} ({porcentaje_activo:+.2f}%)")
            print(f"    📅 Días tenencia: {dias_tenencia}")
            print(f"    📈 Rendimiento anualizado: {rendimiento_anualizado:+.1f}%")
            print()
    
    def save_portfolio_to_db(self, cartera_data, db_manager):
        """Guarda los datos de la cartera en la base de datos"""
        try:
            if not cartera_data:
                return False
            
            print("💾 Guardando datos de cartera en BD...")
            
            portfolio_snapshot = {
                'fecha': cartera_data['timestamp'].date().isoformat(),
                'dinero_disponible': cartera_data['dinero_disponible'],
                'valor_total_cartera': cartera_data['valor_total_cartera'],
                'total_invertido': cartera_data['total_invertido'],
                'ganancia_perdida_total': cartera_data['ganancia_perdida_total'],
                'cantidad_activos': len(cartera_data['activos'])
            }
            
            result = db_manager.supabase.table('portfolio_snapshots').upsert(portfolio_snapshot).execute()
            
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
                    'ganancia_perdida_porcentaje': activo['ganancia_perdida_porcentaje'],
                    'dias_tenencia': activo.get('dias_tenencia', 0)
                }
                
                db_manager.supabase.table('portfolio_activos').upsert(activo_detail).execute()
            
            print("✅ Datos de cartera guardados en BD")
            return True
            
        except Exception as e:
            print(f"❌ Error guardando cartera en BD: {str(e)}")
            return False