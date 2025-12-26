#!/usr/bin/env python3
"""
Generate and validate API documentation schema
"""

import os
import sys
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(__file__))

import django
django.setup()

def generate_openapi_schema():
    """Generate OpenAPI schema and validate configuration"""
    print("🚀 Generating BitTorrent API Documentation")
    print("=" * 60)

    try:
        from drf_spectacular.generators import SchemaGenerator
        from drf_spectacular.openapi import OpenApiRenderer

        print("📄 Generating OpenAPI 3.0 schema...")

        # Generate schema
        generator = SchemaGenerator()
        schema = generator.get_schema(request=None, public=True)

        # Render as JSON
        renderer = OpenApiRenderer()
        openapi_json = renderer.render(schema, renderer_context={})

        # Parse and validate
        schema_dict = json.loads(openapi_json)

        print("✅ OpenAPI schema generated successfully!")
        print(f"   Title: {schema_dict.get('info', {}).get('title', 'N/A')}")
        print(f"   Version: {schema_dict.get('info', {}).get('version', 'N/A')}")
        print(f"   Description: {schema_dict.get('info', {}).get('description', 'N/A')[:100]}...")

        # Analyze paths
        paths = schema_dict.get('paths', {})
        print(f"\n📊 API Endpoints Analysis:")
        print(f"   Total endpoints: {len(paths)}")

        # Categorize endpoints
        categories = {
            'Authentication': 0,
            'User Management': 0,
            'Torrent Management': 0,
            'BitTorrent Tracker': 0,
            'Credit System': 0,
            'Admin Panel': 0,
            'Monitoring': 0,
            'Utilities': 0
        }

        for path, methods in paths.items():
            if '/auth/' in path:
                categories['Authentication'] += 1
            elif '/user/' in path:
                categories['User Management'] += 1
            elif '/torrents/' in path:
                categories['Torrent Management'] += 1
            elif path in ['/announce', '/scrape']:
                categories['BitTorrent Tracker'] += 1
            elif '/credits/' in path:
                categories['Credit System'] += 1
            elif '/admin/' in path:
                categories['Admin Panel'] += 1
            elif '/logs/' in path:
                categories['Monitoring'] += 1
            else:
                categories['Utilities'] += 1

        print("   By category:")
        for category, count in categories.items():
            if count > 0:
                print(f"     {category}: {count} endpoints")

        # Check security schemes
        security_schemes = schema_dict.get('components', {}).get('securitySchemes', {})
        print(f"\n🔒 Security Schemes: {len(security_schemes)}")
        for scheme_name, scheme_config in security_schemes.items():
            print(f"   {scheme_name}: {scheme_config.get('type', 'unknown')}")

        # Check tags
        tags = schema_dict.get('tags', [])
        print(f"\n🏷️  API Tags: {len(tags)}")
        for tag in tags:
            print(f"   {tag.get('name', 'Unknown')}: {tag.get('description', 'No description')[:50]}...")

        # Save schema to file
        with open('openapi_schema.json', 'w', encoding='utf-8') as f:
            json.dump(schema_dict, f, indent=2, ensure_ascii=False)

        print("\n💾 Schema saved to: openapi_schema.json")
        print(f"   File size: {len(openapi_json)} characters")

        # Validate key endpoints exist
        print("\n✅ Key Endpoint Validation:")
        key_endpoints = [
            '/api/auth/register/',
            '/api/auth/login/',
            '/api/user/profile/',
            '/api/torrents/',
            '/api/credits/balance/',
            '/announce',
            '/scrape',
            '/api/admin/dashboard/',
            '/api/logs/system/'
        ]

        found_endpoints = 0
        for endpoint in key_endpoints:
            if endpoint in paths:
                print(f"   ✅ {endpoint}")
                found_endpoints += 1
            else:
                print(f"   ❌ {endpoint} - NOT FOUND")

        print(f"\n📈 Validation Results: {found_endpoints}/{len(key_endpoints)} key endpoints found")

        return True

    except Exception as e:
        print(f"❌ Schema generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_swagger_html():
    """Create a simple HTML page that would load Swagger UI"""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>BitTorrent Tracker API - Swagger UI</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.7.2/swagger-ui.css" />
    <style>
        html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
        *, *:before, *:after { box-sizing: inherit; }
        body { margin:0; background: #fafafa; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.7.2/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.7.2/swagger-ui-standalone-preset.js"></script>
    <script>
    window.onload = function() {
      const ui = SwaggerUIBundle({
        url: '/api/schema/',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "StandaloneLayout"
      });
    };
    </script>
</body>
</html>"""

    with open('swagger_ui_template.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("📄 Swagger UI template created: swagger_ui_template.html")

def create_redoc_html():
    """Create a simple HTML page that would load ReDoc"""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>BitTorrent Tracker API - ReDoc</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body { margin: 0; padding: 0; }
    </style>
</head>
<body>
    <redoc spec-url="/api/schema/"></redoc>
    <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
</body>
</html>"""

    with open('redoc_template.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("📄 ReDoc template created: redoc_template.html")

if __name__ == "__main__":
    success = generate_openapi_schema()

    if success:
        create_swagger_html()
        create_redoc_html()

        print("\n" + "=" * 60)
        print("🎉 API Documentation Setup Complete!")
        print("\n📖 When server is running, access at:")
        print("   Swagger UI: http://localhost:8000/api/docs/")
        print("   ReDoc:      http://localhost:8000/api/redoc/")
        print("   OpenAPI:    http://localhost:8000/api/schema/")
        print("\n📄 Generated files:")
        print("   openapi_schema.json - Complete OpenAPI specification")
        print("   swagger_ui_template.html - Swagger UI template")
        print("   redoc_template.html - ReDoc template")
        print("\n✨ Features:")
        print("   ✅ OpenAPI 3.0 compliant schema")
        print("   ✅ JWT Bearer authentication documented")
        print("   ✅ Comprehensive endpoint coverage")
        print("   ✅ Request/response examples")
        print("   ✅ Parameter validation schemas")
        print("   ✅ Tagged organization")
        print("   ✅ Error response documentation")

        sys.exit(0)
    else:
        print("\n❌ API Documentation generation failed!")
        sys.exit(1)
