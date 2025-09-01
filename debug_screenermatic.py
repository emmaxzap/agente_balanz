#!/usr/bin/env python3
# debug_screenermatic.py - Debug único para entender la estructura de Screenermatic
from playwright.sync_api import sync_playwright

def debug_screenermatic():
    """Debug la estructura real de Screenermatic para encontrar dónde están los ratios"""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # SIEMPRE hacer login primero
        print("Haciendo login en Screenermatic...")
        login_url = "https://www.screenermatic.com/login.php"
        page.goto(login_url, wait_until='networkidle')
        
        # Hacer login
        print("Rellenando formulario de login...")
        page.fill('#email', 'mhv220@gmail.com')
        page.fill('#password', 'Gesti@n07')
        
        # Hacer click en submit
        print("Enviando formulario...")
        page.click('input[type="submit"][name="form2"]')
        page.wait_for_timeout(5000)
        
        # Ahora ir a la página de ratios
        url = "https://www.screenermatic.com/general_ratios.php"
        print(f"Navegando a ratios: {url}")
        page.goto(url, wait_until='networkidle')
        page.wait_for_timeout(3000)
        
        target_tickers = ['ALUA', 'COME', 'EDN', 'METR', 'TECO2']
        
        print("\n=== ANÁLISIS DE ESTRUCTURA ===")
        
        # 1. Buscar dónde están los tickers
        print("\n1. UBICACIÓN DE TICKERS:")
        for ticker in target_tickers:
            elements = page.locator(f'text="{ticker}"').all()
            print(f"\n{ticker}: {len(elements)} elementos encontrados")
            
            for i, element in enumerate(elements):
                # Ver el HTML del elemento
                html = element.inner_html()
                print(f"  Elemento {i}: {html}")
                
                # Ver la fila padre
                parent_row = element.locator('xpath=ancestor::tr').first
                if parent_row.count() > 0:
                    cells = parent_row.locator('td, th').all()
                    print(f"  Fila padre: {len(cells)} celdas")
                    
                    # Mostrar contenido de las primeras 10 celdas
                    cell_contents = []
                    for j, cell in enumerate(cells[:10]):
                        content = cell.text_content().strip()[:20]
                        cell_contents.append(f"[{j}]: '{content}'")
                    print(f"  Contenido: {cell_contents}")
        
        # 2. Buscar filas con muchas celdas (datos reales)
        print("\n2. FILAS CON MUCHAS CELDAS (DATOS):")
        all_rows = page.locator('tr').all()
        data_rows = []
        
        for i, row in enumerate(all_rows):
            cells = row.locator('td, th').all()
            cell_count = len(cells)
            
            if cell_count >= 10:
                row_text = row.text_content()
                
                # Ver si contiene tickers argentinos
                found_tickers = [t for t in target_tickers if t in row_text]
                
                data_rows.append({
                    'index': i,
                    'cells': cell_count,
                    'tickers': found_tickers,
                    'sample': row_text[:100]
                })
        
        print(f"Total filas con ≥10 celdas: {len(data_rows)}")
        
        for row_info in data_rows[:10]:  # Mostrar primeras 10
            print(f"  Fila {row_info['index']}: {row_info['cells']} celdas")
            if row_info['tickers']:
                print(f"    CONTIENE TICKERS: {row_info['tickers']}")
            print(f"    Muestra: {row_info['sample']}")
        
        # 3. Buscar específicamente filas que tengan tanto ticker como datos numéricos
        print("\n3. FILAS CON TICKERS Y DATOS NUMÉRICOS:")
        
        for ticker in target_tickers:
            print(f"\nBuscando {ticker} en filas de datos...")
            
            for row_info in data_rows:
                if ticker in row_info['sample']:
                    row = all_rows[row_info['index']]
                    cells = row.locator('td, th').all()
                    
                    # Extraer contenido de todas las celdas
                    cell_data = []
                    numeric_count = 0
                    
                    for cell in cells:
                        content = cell.text_content().strip()
                        cell_data.append(content)
                        
                        # Contar valores que parecen numéricos
                        if content and content.replace('.', '').replace('-', '').replace(',', '').isdigit():
                            numeric_count += 1
                    
                    if numeric_count >= 5:  # Si hay al menos 5 valores numéricos
                        print(f"  ENCONTRADO en fila {row_info['index']}: {len(cells)} celdas, {numeric_count} valores numéricos")
                        print(f"  Primeras 15 celdas: {cell_data[:15]}")
        
        browser.close()

if __name__ == "__main__":
    debug_screenermatic()