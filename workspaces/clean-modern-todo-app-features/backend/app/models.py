# backend/app/models.py
"""
Database Models - Seed Template

Derek will OVERWRITE this file with actual Beanie Document models.
This seed exists so that:
1. database.py doesn't fail on import before Derek generates real models
2. The healing pipeline has a fallback

When Derek generates models, he writes the COMPLETE file - not patches.
"""


# Derek will replace this entire file with project-specific models.
# Example of what Derek generates:
#
# class Product(Document):
#     name: str = Field(..., description="Product name")
#     price: float = Field(..., ge=0)
#     created_at: datetime = Field(default_factory=datetime.utcnow)
#     
#     class Settings:
#         name = "products"


# Export all model classes for auto-discovery by database.py
# Derek's models.py will define actual __all__
__all__ = []
