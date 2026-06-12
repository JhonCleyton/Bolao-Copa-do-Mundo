"""
Country flags utility
Maps country codes to flag emojis and provides helper functions
"""

# Country code to flag emoji mapping
# Uses regional indicator symbols (🇦 + 🇧 = 🇦🇧)
COUNTRY_FLAGS = {
    # South America
    'BRA': '🇧🇷',  # Brazil
    'ARG': '🇦🇷',  # Argentina
    'URU': '🇺🇾',  # Uruguay
    'COL': '🇨🇴',  # Colombia
    'CHI': '🇨🇱',  # Chile
    'ECU': '🇪🇨',  # Ecuador
    'PER': '🇵🇪',  # Peru
    'PAR': '🇵🇾',  # Paraguay
    'BOL': '🇧🇴',  # Bolivia
    'VEN': '🇻🇪',  # Venezuela
    
    # North/Central America
    'MEX': '🇲🇽',  # Mexico
    'USA': '🇺🇸',  # United States
    'CAN': '🇨🇦',  # Canada
    'CRC': '🇨🇷',  # Costa Rica
    'PAN': '🇵🇦',  # Panama
    'HON': '🇭🇳',  # Honduras
    'JAM': '🇯🇲',  # Jamaica
    'HAI': '🇭🇹',  # Haiti
    
    # Europe
    'GER': '🇩🇪',  # Germany
    'DEU': '🇩🇪',  # Germany (ISO)
    'FRA': '🇫🇷',  # France
    'ESP': '🇪🇸',  # Spain
    'ENG': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',  # England
    'GBR': '🇬🇧',  # Great Britain
    'POR': '🇵🇹',  # Portugal
    'ITA': '🇮🇹',  # Italy
    'NED': '🇳🇱',  # Netherlands
    'NLD': '🇳🇱',  # Netherlands (ISO)
    'BEL': '🇧🇪',  # Belgium
    'CRO': '🇭🇷',  # Croatia
    'HRV': '🇭🇷',  # Croatia (ISO)
    'SUI': '🇨🇭',  # Switzerland
    'CHE': '🇨🇭',  # Switzerland (ISO)
    'DEN': '🇩🇰',  # Denmark
    'DNK': '🇩🇰',  # Denmark (ISO)
    'POL': '🇵🇱',  # Poland
    'POL': '🇵🇱',  # Poland (ISO)
    'SCO': '🏴󠁧󠁢󠁳󠁣󠁯󠁿',  # Scotland
    'WAL': '🏴󠁧󠁢󠁷󠁬󠁳󠁿',  # Wales
    'UKR': '🇺🇦',  # Ukraine
    'AUT': '🇦🇹',  # Austria
    'CZE': '🇨🇿',  # Czech Republic
    'CZE': '🇨🇿',  # Czech Republic
    'SRB': '🇷🇸',  # Serbia
    'TUR': '🇹🇷',  # Turkey
    'HUN': '🇭🇺',  # Hungary
    'SVK': '🇸🇰',  # Slovakia
    'SVN': '🇸🇮',  # Slovenia
    'ROU': '🇷🇴',  # Romania
    'ALB': '🇦🇱',  # Albania
    'GEO': '🇬🇪',  # Georgia
    
    # Africa
    'MAR': '🇲🇦',  # Morocco
    'SEN': '🇸🇳',  # Senegal
    'TUN': '🇹🇳',  # Tunisia
    'ALG': '🇩🇿',  # Algeria
    'EGY': '🇪🇬',  # Egypt
    'CMR': '🇨🇲',  # Cameroon
    'GHA': '🇬🇭',  # Ghana
    'NGA': '🇳🇬',  # Nigeria
    'CIV': '🇨🇮',  # Ivory Coast
    'RSA': '🇿🇦',  # South Africa
    
    # Asia
    'JPN': '🇯🇵',  # Japan
    'KOR': '🇰🇷',  # South Korea
    'KSA': '🇸🇦',  # Saudi Arabia
    'IRN': '🇮🇷',  # Iran
    'AUS': '🇦🇺',  # Australia
    'QAT': '🇶🇦',  # Qatar
    'UZB': '🇺🇿',  # Uzbekistan
    'IRQ': '🇮🇶',  # Iraq
    'JOR': '🇯🇴',  # Jordan
    'UAE': '🇦🇪',  # UAE
    
    # Oceania
    'NZL': '🇳🇿',  # New Zealand
    
    # Special/placeholder
    'TBD': '🏳️',   # To be determined
    'W': '🏳️',     # Winner placeholder
    'L': '🏳️',     # Loser placeholder
}

# Additional name-to-code mappings for lookup
COUNTRY_NAME_TO_CODE = {
    'brasil': 'BRA',
    'brazil': 'BRA',
    'argentina': 'ARG',
    'uruguai': 'URU',
    'uruguay': 'URU',
    'colombia': 'COL',
    'chile': 'CHI',
    'equador': 'ECU',
    'ecuador': 'ECU',
    'peru': 'PER',
    'paraguai': 'PAR',
    'paraguay': 'PAR',
    'bolivia': 'BOL',
    'venezuela': 'VEN',
    
    'mexico': 'MEX',
    'méxico': 'MEX',
    'estados unidos': 'USA',
    'united states': 'USA',
    'eua': 'USA',
    'usa': 'USA',
    'canada': 'CAN',
    'canadá': 'CAN',
    'costa rica': 'CRC',
    'panama': 'PAN',
    'panamá': 'PAN',
    'honduras': 'HON',
    'jamaica': 'JAM',
    'haiti': 'HAI',
    'haití': 'HAI',
    
    'alemanha': 'GER',
    'germany': 'GER',
    'franca': 'FRA',
    'frança': 'FRA',
    'france': 'FRA',
    'espanha': 'ESP',
    'spain': 'ESP',
    'inglaterra': 'ENG',
    'england': 'ENG',
    'portugal': 'POR',
    'italia': 'ITA',
    'italy': 'ITA',
    'holanda': 'NED',
    'netherlands': 'NED',
    'belgica': 'BEL',
    'bélgica': 'BEL',
    'belgium': 'BEL',
    'croacia': 'CRO',
    'croatia': 'CRO',
    'croácia': 'CRO',
    'suica': 'SUI',
    'suíça': 'SUI',
    'switzerland': 'SUI',
    'dinamarca': 'DEN',
    'denmark': 'DEN',
    'polonia': 'POL',
    'polônia': 'POL',
    'poland': 'POL',
    'escocia': 'SCO',
    'scotland': 'SCO',
    'escócia': 'SCO',
    'pais de gales': 'WAL',
    'wales': 'WAL',
    'país de gales': 'WAL',
    'ucrania': 'UKR',
    'ukraine': 'UKR',
    'austria': 'AUT',
    'áustria': 'AUT',
    'republica tcheca': 'CZE',
    'tcheca': 'CZE',
    'czech republic': 'CZE',
    'república tcheca': 'CZE',
    'servia': 'SRB',
    'sérvia': 'SRB',
    'serbia': 'SRB',
    'turquia': 'TUR',
    'turkey': 'TUR',
    'hungria': 'HUN',
    'hungary': 'HUN',
    'eslovaquia': 'SVK',
    'slovakia': 'SVK',
    'eslovenia': 'SVN',
    'slovenia': 'SVN',
    'romenia': 'ROU',
    'romênia': 'ROU',
    'romania': 'ROU',
    'albania': 'ALB',
    'albânia': 'ALB',
    'georgia': 'GEO',
    'geórgia': 'GEO',
    
    'marrocos': 'MAR',
    'morocco': 'MAR',
    'senegal': 'SEN',
    'tunisia': 'TUN',
    'tunísia': 'TUN',
    'argelia': 'ALG',
    'argélia': 'ALG',
    'algeria': 'ALG',
    'egito': 'EGY',
    'egypt': 'EGY',
    'camaroes': 'CMR',
    'cameroon': 'CMR',
    ' camarões': 'CMR',
    'gana': 'GHA',
    'ghana': 'GHA',
    'nigeria': 'NGA',
    'náigeria': 'NGA',
    'costa do marfim': 'CIV',
    'ivory coast': 'CIV',
    'africa do sul': 'RSA',
    'áfrica do sul': 'RSA',
    'south africa': 'RSA',
    
    'japao': 'JPN',
    'japão': 'JPN',
    'japan': 'JPN',
    'coreia do sul': 'KOR',
    'south korea': 'KOR',
    'arabia saudita': 'KSA',
    'arábia saudita': 'KSA',
    'saudi arabia': 'KSA',
    'ira': 'IRN',
    'irã': 'IRN',
    'iran': 'IRN',
    'australia': 'AUS',
    'austrália': 'AUS',
    'catar': 'QAT',
    'qatar': 'QAT',
    
    'nova zelandia': 'NZL',
    'nova Zelândia': 'NZL',
    'new zealand': 'NZL',
}


def get_flag_emoji(code: str) -> str:
    """Get flag emoji from country code"""
    if not code:
        return '🏳️'
    
    code_upper = code.upper().strip()
    
    # Direct lookup
    if code_upper in COUNTRY_FLAGS:
        return COUNTRY_FLAGS[code_upper]
    
    # Try to construct from letters (for 2-letter codes)
    if len(code_upper) == 2:
        # Convert to regional indicator symbols
        # A = 127462 (🇦), B = 127463 (🇧), etc.
        try:
            flag = ''.join(chr(127397 + ord(c)) for c in code_upper if 'A' <= c <= 'Z')
            return flag if len(flag) == 2 else '🏳️'
        except:
            return '🏳️'
    
    return '🏳️'


def get_flag_by_name(name: str) -> str:
    """Get flag emoji from country name"""
    if not name:
        return '🏳️'
    
    name_lower = name.lower().strip()
    
    # Direct lookup
    if name_lower in COUNTRY_NAME_TO_CODE:
        code = COUNTRY_NAME_TO_CODE[name_lower]
        return get_flag_emoji(code)
    
    # Try partial matches
    for key, code in COUNTRY_NAME_TO_CODE.items():
        if key in name_lower or name_lower in key:
            return get_flag_emoji(code)
    
    return '🏳️'


def get_flag(code: str = None, name: str = None) -> str:
    """Get flag emoji from code or name"""
    if code:
        return get_flag_emoji(code)
    if name:
        return get_flag_by_name(name)
    return '🏳️'


def format_team_with_flag(team_name: str, team_code: str = None) -> str:
    """Format team name with flag emoji"""
    flag = get_flag(code=team_code, name=team_name)
    return f"{flag} {team_name}"


# Standings position change indicators
def get_position_change_indicator(current_pos: int, previous_pos: int) -> str:
    """Get indicator for position change"""
    if previous_pos == 0 or current_pos == previous_pos:
        return '<span class="text-muted">●</span>'  # No change
    elif current_pos < previous_pos:
        diff = previous_pos - current_pos
        arrows = '↑' * min(diff, 3)
        return f'<span class="text-success fw-bold">{arrows} {diff}</span>'
    else:
        diff = current_pos - previous_pos
        arrows = '↓' * min(diff, 3)
        return f'<span class="text-danger fw-bold">{arrows} {diff}</span>'
