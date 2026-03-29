"""
API Routes 검증 스크립트

모든 라우터가 제대로 로드되는지 확인.

Usage:
    python test_routes.py
"""

import sys


def test_router_imports():
    """라우터 import 테스트"""
    print("📝 Testing router imports...")
    
    try:
        from api.routes import (
            users_router,
            sessions_router,
            conversations_router,
            memories_router,
            garden_router,
            analysis_router,
        )
        
        routers = {
            "users": users_router,
            "sessions": sessions_router,
            "conversations": conversations_router,
            "memories": memories_router,
            "garden": garden_router,
            "analysis": analysis_router,
        }
        
        for name, router in routers.items():
            print(f"   ✅ {name}_router loaded: prefix={router.prefix}, tags={router.tags}")
        
        print("   ✅ All routers imported successfully")
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to import routers: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_app_initialization():
    """FastAPI app 초기화 테스트"""
    print("\n📝 Testing FastAPI app initialization...")
    
    try:
        from api.main import app
        
        print(f"   ✅ App title: {app.title}")
        print(f"   ✅ App version: {app.version}")
        print(f"   ✅ Total routes: {len(app.routes)}")
        
        # 라우터별 엔드포인트 개수 확인
        route_counts = {}
        for route in app.routes:
            if hasattr(route, 'path') and route.path.startswith('/api/v1'):
                prefix = route.path.split('/')[3] if len(route.path.split('/')) > 3 else 'root'
                route_counts[prefix] = route_counts.get(prefix, 0) + 1
        
        print("\n   📊 Routes by module:")
        for module, count in sorted(route_counts.items()):
            print(f"      - {module}: {count} endpoints")
        
        print("\n   ✅ App initialized successfully")
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to initialize app: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_route_details():
    """라우트 상세 정보 확인"""
    print("\n📝 Testing route details...")
    
    try:
        from api.main import app
        
        print("\n   📋 Available endpoints:")
        
        api_routes = [route for route in app.routes if hasattr(route, 'path') and route.path.startswith('/api/v1')]
        api_routes_sorted = sorted(api_routes, key=lambda r: r.path)
        
        for route in api_routes_sorted:
            methods = ', '.join(route.methods) if hasattr(route, 'methods') else 'N/A'
            print(f"      {methods:10} {route.path}")
        
        print(f"\n   ✅ Total API endpoints: {len(api_routes)}")
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to get route details: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("🔍 API Routes Validation Test")
    print("=" * 60)
    
    results = []
    
    # Test 1: Router imports
    results.append(test_router_imports())
    
    # Test 2: App initialization
    results.append(test_app_initialization())
    
    # Test 3: Route details
    results.append(test_route_details())
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ All route tests passed!")
        print("=" * 60)
        print("\n💡 Next steps:")
        print("   1. Start the server: uvicorn api.main:app --reload")
        print("   2. Visit API docs: http://localhost:8000/docs")
        print("   3. Implement service classes:")
        print("      - services/user_service.py")
        print("      - services/session_service.py")
        print("      - services/conversation_service.py")
        print("      - services/memory_service.py")
        print("      - services/garden_service.py")
        print("      - services/analysis_service.py")
        return 0
    else:
        print("❌ Some route tests failed!")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
