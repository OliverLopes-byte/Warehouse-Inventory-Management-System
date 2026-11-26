import unittest

from main import merge_openapi_documents, swagger


def service_document(path: str, method: str, operation_id: str) -> dict:
    return {
        "openapi": "3.1.0",
        "info": {"title": "Service", "version": "1.0.0"},
        "paths": {
            path: {
                method: {
                    "operationId": operation_id,
                    "tags": ["Shared"],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Shared"}
                            }
                        }
                    },
                }
            }
        },
        "components": {
            "schemas": {"Shared": {"type": "object"}},
            "securitySchemes": {
                "BearerAuth": {"type": "http", "scheme": "bearer"}
            },
        },
        "security": [{"BearerAuth": []}],
        "tags": [{"name": "Shared"}],
    }


class MergeOpenAPIDocumentsTests(unittest.TestCase):
    def test_prefixes_paths_and_namespaces_components_and_operations(self):
        merged = merge_openapi_documents(
            {"openapi": "3.1.0", "info": {}, "paths": {"/health": {}}},
            {
                "auth": service_document("/auth/login", "post", "login"),
                "catalog": service_document("/products", "get", "list_products"),
            },
        )

        self.assertIn("/health", merged["paths"])
        self.assertIn("/api/auth/auth/login", merged["paths"])
        self.assertIn("/api/catalog/products", merged["paths"])
        self.assertIn("auth__Shared", merged["components"]["schemas"])
        self.assertIn("catalog__Shared", merged["components"]["schemas"])

        auth_operation = merged["paths"]["/api/auth/auth/login"]["post"]
        self.assertEqual(auth_operation["operationId"], "auth_login")
        self.assertEqual(auth_operation["tags"], ["Auth - Shared"])
        self.assertEqual(
            auth_operation["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/auth__Shared",
        )
        self.assertEqual(auth_operation["security"], [{"BearerAuth": []}])

        catalog_operation = merged["paths"]["/api/catalog/products"]["get"]
        self.assertEqual(catalog_operation["operationId"], "catalog_list_products")
        self.assertEqual(catalog_operation["security"], [{"BearerAuth": []}])
        self.assertEqual(
            list(merged["components"]["securitySchemes"]),
            ["BearerAuth"],
        )
        self.assertEqual(merged["servers"], [{"url": "/"}])

    def test_password_oauth_schemes_become_one_pasteable_bearer_scheme(self):
        auth = service_document("/auth/login", "post", "login")
        protected_services = {
            "catalog": service_document("/products", "get", "list_products"),
            "warehouse": service_document("/stock/balance", "get", "stock_balance"),
            "reports": service_document("/reports/valuation", "get", "valuation"),
        }
        documents = {"auth": auth, **protected_services}
        for document in documents.values():
            document["components"]["securitySchemes"] = {
                "OAuth2PasswordBearer": {
                    "type": "oauth2",
                    "flows": {
                        "password": {
                            "tokenUrl": "/api/auth/auth/login",
                            "scopes": {},
                        }
                    },
                }
            }
        auth["paths"]["/auth/login"]["post"]["security"] = []
        for document in protected_services.values():
            path_item = next(iter(document["paths"].values()))
            operation = next(iter(path_item.values()))
            operation["security"] = [{"OAuth2PasswordBearer": []}]

        merged = merge_openapi_documents(
            {"openapi": "3.1.0", "info": {}, "paths": {}},
            documents,
        )

        self.assertEqual(
            merged["components"]["securitySchemes"],
            {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": (
                        "Paste the access token returned by "
                        "POST /api/auth/auth/login."
                    ),
                }
            },
        )
        for service, document in protected_services.items():
            path, path_item = next(iter(document["paths"].items()))
            method = next(iter(path_item))
            self.assertEqual(
                merged["paths"][f"/api/{service}{path}"][method]["security"],
                [{"BearerAuth": []}],
            )
        self.assertEqual(
            merged["paths"]["/api/auth/auth/login"]["post"]["security"],
            [],
        )

    def test_different_security_schemes_remain_separate(self):
        catalog = service_document("/products", "get", "list_products")
        catalog["components"]["securitySchemes"]["BearerAuth"] = {
            "type": "apiKey",
            "in": "header",
            "name": "X-Token",
        }

        merged = merge_openapi_documents(
            {"openapi": "3.1.0", "info": {}, "paths": {}},
            {
                "auth": service_document("/auth/login", "post", "login"),
                "catalog": catalog,
            },
        )

        self.assertIn("BearerAuth", merged["components"]["securitySchemes"])
        self.assertIn("catalog__BearerAuth", merged["components"]["securitySchemes"])
        self.assertEqual(
            merged["paths"]["/api/catalog/products"]["get"]["security"],
            [{"catalog__BearerAuth": []}],
        )

    def test_scoped_oauth2_schemes_are_not_converted_to_bearer_auth(self):
        catalog = service_document("/products", "get", "list_products")
        catalog["components"]["securitySchemes"]["OAuth2PasswordBearer"] = {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/another-login",
                    "scopes": {"catalog:write": "Write catalog data"},
                }
            },
        }
        catalog["paths"]["/products"]["get"]["security"] = [
            {"OAuth2PasswordBearer": ["catalog:write"]}
        ]

        merged = merge_openapi_documents(
            {"openapi": "3.1.0", "info": {}, "paths": {}},
            {
                "auth": service_document("/auth/login", "post", "login"),
                "catalog": catalog,
            },
        )

        scheme = merged["components"]["securitySchemes"]["OAuth2PasswordBearer"]
        self.assertEqual(scheme["type"], "oauth2")
        self.assertEqual(
            merged["paths"]["/api/catalog/products"]["get"]["security"],
            [{"OAuth2PasswordBearer": ["catalog:write"]}],
        )


class GatewayDocsTests(unittest.TestCase):
    def test_swagger_page_points_to_combined_spec(self):
        page = swagger()

        self.assertIn("/openapi.json", page.body.decode())
        self.assertNotIn("service-selector", page.body.decode())


if __name__ == "__main__":
    unittest.main()
