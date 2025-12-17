# app/handlers/archetype_guidance.py
"""
Archetype-Specific UI Guidance for Frontend Mock Generation.

This module provides archetype-aware prompts that guide Derek to generate
different UI patterns based on the project type. This is the key to generating
diverse applications beyond simple CRUD.

ARCHETYPES SUPPORTED:
- admin_dashboard: Data tables, charts, statistics, filters
- saas_app: Multi-tenant, auth, subscription, team features
- content_platform: Blog/CMS, posts, categories, media library
- landing_page: Marketing, hero sections, CTAs, testimonials
- realtime_collab: Chat, messaging, presence, live updates
- ecommerce_store: Products, cart, checkout, inventory
- project_management: Boards, lists, kanban, timelines
"""

from typing import Dict


# ═══════════════════════════════════════════════════════
# ARCHETYPE UI PATTERNS - What makes each archetype unique
# ═══════════════════════════════════════════════════════

ARCHETYPE_UI_GUIDANCE: Dict[str, Dict[str, str]] = {
    
    "admin_dashboard": {
        "description": "Internal admin dashboard with data management",
        "ui_focus": """
🎯 ADMIN DASHBOARD UI PATTERNS:

**PRIMARY COMPONENTS:**
- Data tables with sorting, filtering, pagination (use shadcn Table)
- Statistics cards showing KPIs (total, active, pending counts)
- Charts/graphs for trends (can use recharts or simple CSS bars)
- Sidebar navigation with sections (Dashboard, Users, Settings)
- Search and filter bar at the top

**LAYOUT PATTERN:**
```jsx
<div className="flex">
  <aside className="w-64 bg-sidebar">
    <Navigation />
  </aside>
  <main className="flex-1 p-6">
    <StatsCards />
    <DataTable />
  </main>
</div>
```

**MOCK DATA STRUCTURE:**
```javascript
export const mockStats = {
  total: 1234,
  active: 890,
  pending: 234,
  growth: "+12.5%"
};

export const mockTableData = [
  { id: 1, name: "...", status: "Active", created: "2024-01-15", actions: [...] },
  // Include 10-15 rows for realistic pagination demo
];
```

**REQUIRED FEATURES:**
- [ ] Stats cards with icons (Users, Revenue, Orders, Growth)
- [ ] Filterable data table with status badges
- [ ] Bulk action buttons (Export, Delete Selected)
- [ ] Search input with icon
- [ ] Pagination controls
""",
        "additional_pages": ["DashboardPage", "UsersPage", "SettingsPage"],
        "key_components": ["StatsCard", "DataTable", "Sidebar", "FilterBar"],
    },
    
    "saas_app": {
        "description": "Multi-tenant SaaS with auth and subscriptions",
        "ui_focus": """
🎯 SAAS APPLICATION UI PATTERNS:

**PRIMARY COMPONENTS:**
- User authentication UI (Login/Signup forms - can be mocked)
- Subscription tier cards (Free, Pro, Enterprise)
- Team member management (invite, roles, permissions)
- Settings with multiple tabs (Profile, Billing, Team, API)
- Activity feed or changelog

**LAYOUT PATTERN:**
```jsx
<div className="min-h-screen">
  <header className="border-b">
    <nav>Logo | Features | Pricing | Login</nav>
  </header>
  <main>
    <HeroSection />
    <PricingCards />
    <FeatureGrid />
  </main>
</div>
```

**MOCK DATA STRUCTURE:**
```javascript
export const mockUser = {
  id: "1",
  name: "John Doe",
  email: "john@company.com",
  plan: "Pro",
  teamId: "team-123"
};

export const mockPricingTiers = [
  { name: "Starter", price: 0, features: ["5 projects", "1GB storage"] },
  { name: "Pro", price: 29, features: ["Unlimited", "10GB", "Priority support"], popular: true },
  { name: "Enterprise", price: 99, features: ["Custom", "Unlimited", "SLA", "SSO"] }
];

export const mockTeamMembers = [
  { id: 1, name: "Jane", role: "Admin", avatar: "..." },
  { id: 2, name: "Bob", role: "Member", avatar: "..." }
];
```

**REQUIRED FEATURES:**
- [ ] Pricing comparison table/cards
- [ ] Feature list with checkmarks
- [ ] Team member cards with role badges
- [ ] Settings tabs (shadcn Tabs component)
- [ ] Invite member dialog
""",
        "additional_pages": ["PricingPage", "TeamPage", "SettingsPage"],
        "key_components": ["PricingCard", "TeamMemberCard", "SettingsTabs", "InviteDialog"],
    },
    
    "content_platform": {
        "description": "Blog, CMS, or content publishing platform",
        "ui_focus": """
🎯 CONTENT PLATFORM UI PATTERNS:

**PRIMARY COMPONENTS:**
- Rich content cards (thumbnail, title, excerpt, metadata)
- Category/tag sidebar or horizontal tabs
- Author byline with avatar
- Reading time estimates
- Markdown or rich text preview area

**LAYOUT PATTERN:**
```jsx
<div className="max-w-4xl mx-auto">
  <header className="py-8">
    <h1>Blog Title</h1>
    <CategoryTabs />
  </header>
  <main className="grid gap-6">
    {posts.map(post => <ArticleCard key={post.id} {...post} />)}
  </main>
  <aside className="hidden lg:block">
    <PopularPosts />
    <TagCloud />
  </aside>
</div>
```

**MOCK DATA STRUCTURE:**
```javascript
export const mockArticles = [
  {
    id: "1",
    title: "Getting Started with React 19",
    excerpt: "Learn the new features in React 19...",
    author: { name: "Sarah Chen", avatar: "https://i.pravatar.cc/40?u=1" },
    category: "Tutorial",
    tags: ["react", "javascript", "web"],
    readingTime: "5 min",
    publishedAt: "2024-01-15",
    coverImage: "https://picsum.photos/800/400?random=1"
  },
  // 5-6 articles with different categories
];

export const mockCategories = [
  { id: 1, name: "All", count: 24 },
  { id: 2, name: "Tutorial", count: 12 },
  { id: 3, name: "News", count: 8 },
  { id: 4, name: "Opinion", count: 4 }
];
```

**REQUIRED FEATURES:**
- [ ] Article cards with cover images
- [ ] Category filter tabs
- [ ] Author byline with avatar
- [ ] Tag badges (use shadcn Badge)
- [ ] Reading time indicator
- [ ] Featured/pinned post section
""",
        "additional_pages": ["ArticlesPage", "ArticleDetailPage", "CategoryPage"],
        "key_components": ["ArticleCard", "CategoryTabs", "AuthorByline", "TagCloud"],
    },
    
    "landing_page": {
        "description": "Marketing website with hero and CTAs",
        "ui_focus": """
🎯 LANDING PAGE UI PATTERNS:

**PRIMARY COMPONENTS:**
- Hero section with headline, subheadline, CTA buttons
- Feature grid (3-4 features with icons)
- Social proof (testimonials, logos, stats)
- Pricing section (if applicable)
- Footer with links

**LAYOUT PATTERN:**
```jsx
<div className="min-h-screen">
  <nav className="fixed top-0 w-full bg-background/80 backdrop-blur">
    Logo | Features | Pricing | Login | <Button>Get Started</Button>
  </nav>
  
  <section className="pt-32 pb-20 text-center">
    <h1 className="text-5xl font-bold">Main Headline</h1>
    <p className="text-xl text-muted-foreground mt-4">Subheadline here</p>
    <div className="flex gap-4 justify-center mt-8">
      <Button size="lg">Primary CTA</Button>
      <Button size="lg" variant="outline">Secondary CTA</Button>
    </div>
  </section>
  
  <FeatureGrid />
  <TestimonialsSection />
  <CTASection />
  <Footer />
</div>
```

**MOCK DATA STRUCTURE:**
```javascript
export const mockFeatures = [
  { icon: "Zap", title: "Lightning Fast", description: "Built for speed..." },
  { icon: "Shield", title: "Secure by Default", description: "Enterprise-grade..." },
  { icon: "Users", title: "Team Collaboration", description: "Work together..." },
  { icon: "BarChart", title: "Analytics", description: "Track everything..." }
];

export const mockTestimonials = [
  { quote: "This changed everything...", author: "CEO, TechCorp", avatar: "..." },
  { quote: "Best decision we made...", author: "CTO, StartupXYZ", avatar: "..." }
];

export const mockStats = [
  { value: "10k+", label: "Active Users" },
  { value: "99.9%", label: "Uptime" },
  { value: "24/7", label: "Support" }
];
```

**REQUIRED FEATURES:**
- [ ] Sticky navigation with blur effect
- [ ] Hero with gradient text or background
- [ ] Feature grid with Lucide icons
- [ ] Testimonial cards with quotes
- [ ] Stats counter section
- [ ] Newsletter signup form
""",
        "additional_pages": ["LandingPage", "FeaturesPage", "PricingPage"],
        "key_components": ["HeroSection", "FeatureCard", "TestimonialCard", "StatsCounter"],
    },
    
    "realtime_collab": {
        "description": "Real-time collaboration with chat/messaging",
        "ui_focus": """
🎯 REAL-TIME COLLABORATION UI PATTERNS:

**PRIMARY COMPONENTS:**
- Chat message list with sender info and timestamps
- Message input with send button
- User presence indicators (online/offline dots)
- Channel/room sidebar
- Typing indicators

**LAYOUT PATTERN:**
```jsx
<div className="flex h-screen">
  <aside className="w-64 border-r">
    <ChannelList />
    <UserPresence />
  </aside>
  <main className="flex-1 flex flex-col">
    <header className="border-b p-4">
      <h2>#general</h2>
      <span className="text-sm text-muted-foreground">3 members online</span>
    </header>
    <div className="flex-1 overflow-y-auto p-4">
      <MessageList messages={messages} />
    </div>
    <footer className="border-t p-4">
      <MessageInput onSend={handleSend} />
    </footer>
  </main>
</div>
```

**MOCK DATA STRUCTURE:**
```javascript
export const mockChannels = [
  { id: 1, name: "general", unread: 0 },
  { id: 2, name: "random", unread: 3 },
  { id: 3, name: "announcements", unread: 1 }
];

export const mockMessages = [
  { id: 1, sender: "Alice", content: "Hey everyone!", timestamp: "10:30 AM", avatar: "..." },
  { id: 2, sender: "Bob", content: "Hi Alice! How's it going?", timestamp: "10:31 AM", avatar: "..." },
  { id: 3, sender: "You", content: "Good morning team!", timestamp: "10:32 AM", isOwn: true }
];

export const mockOnlineUsers = [
  { id: 1, name: "Alice", status: "online", avatar: "..." },
  { id: 2, name: "Bob", status: "away", avatar: "..." },
  { id: 3, name: "Carol", status: "offline", avatar: "..." }
];
```

**REQUIRED FEATURES:**
- [ ] Message bubbles (different styles for own vs others)
- [ ] Online status indicators (green/yellow/gray dots)
- [ ] Channel sidebar with unread badges
- [ ] Message input with emoji picker placeholder
- [ ] Timestamp grouping (Today, Yesterday, etc.)
""",
        "additional_pages": ["ChatPage", "DirectMessagesPage"],
        "key_components": ["MessageBubble", "ChannelList", "UserPresenceIndicator", "MessageInput"],
    },
    
    "ecommerce_store": {
        "description": "E-commerce with products, cart, checkout",
        "ui_focus": """
🎯 E-COMMERCE STORE UI PATTERNS:

**PRIMARY COMPONENTS:**
- Product grid with images, prices, ratings
- Shopping cart sidebar/drawer
- Product filters (price, category, size)
- Product detail page with gallery
- Checkout form with steps

**LAYOUT PATTERN:**
```jsx
<div className="min-h-screen">
  <header className="border-b">
    <nav>Logo | Categories | Search | Cart(3) | Account</nav>
  </header>
  <main className="max-w-7xl mx-auto p-6">
    <aside className="w-64">
      <ProductFilters />
    </aside>
    <section className="flex-1">
      <ProductGrid products={products} />
    </section>
  </main>
  <CartDrawer />
</div>
```

**MOCK DATA STRUCTURE:**
```javascript
export const mockProducts = [
  {
    id: "1",
    name: "Premium Headphones",
    price: 199.99,
    originalPrice: 249.99,
    image: "https://picsum.photos/400/400?random=1",
    rating: 4.5,
    reviews: 128,
    category: "Electronics",
    inStock: true
  },
  // 8-12 products with different categories
];

export const mockCart = {
  items: [
    { productId: "1", quantity: 2, price: 199.99 },
    { productId: "3", quantity: 1, price: 49.99 }
  ],
  subtotal: 449.97,
  shipping: 9.99,
  total: 459.96
};

export const mockCategories = [
  { id: 1, name: "All Products", count: 48 },
  { id: 2, name: "Electronics", count: 15 },
  { id: 3, name: "Clothing", count: 22 },
  { id: 4, name: "Home & Garden", count: 11 }
];
```

**REQUIRED FEATURES:**
- [ ] Product cards with images, price, sale badge
- [ ] Star rating display
- [ ] Add to Cart button
- [ ] Cart icon with item count
- [ ] Category sidebar with counts
- [ ] Price range filter
- [ ] Grid/List view toggle
""",
        "additional_pages": ["ProductsPage", "ProductDetailPage", "CartPage", "CheckoutPage"],
        "key_components": ["ProductCard", "CartDrawer", "ProductFilters", "PriceDisplay"],
    },
    
    "project_management": {
        "description": "Project/task management with boards and lists",
        "ui_focus": """
🎯 PROJECT MANAGEMENT UI PATTERNS:

**PRIMARY COMPONENTS:**
- Kanban board with draggable columns
- Task cards with assignees, due dates, labels
- Project sidebar with workspace selector
- Task detail modal
- Progress indicators

**LAYOUT PATTERN:**
```jsx
<div className="flex h-screen">
  <aside className="w-64 border-r bg-sidebar">
    <WorkspaceSelector />
    <ProjectList />
  </aside>
  <main className="flex-1 overflow-hidden">
    <header className="border-b p-4 flex justify-between">
      <h1>Sprint 1</h1>
      <div className="flex gap-2">
        <Button>+ Add Task</Button>
        <ViewToggle />
      </div>
    </header>
    <div className="flex-1 overflow-x-auto p-4">
      <KanbanBoard columns={columns} />
    </div>
  </main>
</div>
```

**MOCK DATA STRUCTURE:**
```javascript
export const mockColumns = [
  { id: "todo", title: "To Do", tasks: [...] },
  { id: "in-progress", title: "In Progress", tasks: [...] },
  { id: "review", title: "Review", tasks: [...] },
  { id: "done", title: "Done", tasks: [...] }
];

export const mockTasks = [
  {
    id: "1",
    title: "Design homepage mockup",
    description: "Create initial wireframes...",
    status: "in-progress",
    priority: "high",
    assignee: { name: "Alice", avatar: "..." },
    dueDate: "2024-01-20",
    labels: ["design", "urgent"],
    subtasks: { completed: 2, total: 5 }
  },
  // 10-15 tasks across different columns
];

export const mockProjects = [
  { id: 1, name: "Website Redesign", color: "#3B82F6", taskCount: 24 },
  { id: 2, name: "Mobile App", color: "#10B981", taskCount: 18 },
  { id: 3, name: "API Integration", color: "#F59E0B", taskCount: 12 }
];
```

**REQUIRED FEATURES:**
- [ ] Kanban columns with task counts
- [ ] Task cards with assignee avatars
- [ ] Priority badges (High, Medium, Low)
- [ ] Due date with overdue indicator
- [ ] Subtask progress bar
- [ ] Label/tag chips
- [ ] Quick add task input per column
""",
        "additional_pages": ["BoardPage", "TimelinePage", "CalendarPage"],
        "key_components": ["KanbanColumn", "TaskCard", "ProjectSidebar", "TaskModal"],
    },
}


# ═══════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════

def get_archetype_guidance(archetype: str) -> str:
    """
    Get UI guidance for a specific archetype.
    
    Args:
        archetype: Project archetype (e.g., "admin_dashboard", "ecommerce_store")
        
    Returns:
        Formatted guidance string to inject into Derek's prompt
    """
    guidance = ARCHETYPE_UI_GUIDANCE.get(archetype)
    
    if not guidance:
        # Fallback to generic CRUD guidance
        return """
🎯 GENERAL APPLICATION UI PATTERNS:

Create a clean, functional UI with:
- Main list/grid page for the primary entity
- Create/Edit forms using shadcn Dialog
- Cards for displaying individual items
- Status badges where appropriate
- Search and filter capabilities
"""
    
    return guidance["ui_focus"]


def get_archetype_pages(archetype: str) -> list:
    """Get additional pages recommended for this archetype."""
    guidance = ARCHETYPE_UI_GUIDANCE.get(archetype, {})
    return guidance.get("additional_pages", [])


def get_archetype_components(archetype: str) -> list:
    """Get key components recommended for this archetype."""
    guidance = ARCHETYPE_UI_GUIDANCE.get(archetype, {})
    return guidance.get("key_components", [])


def get_full_archetype_context(archetype: str, entity: str, domain: str) -> str:
    """
    Get complete archetype context for frontend mock generation.
    
    Args:
        archetype: Detected project archetype
        entity: Primary entity name
        domain: Business domain
        
    Returns:
        Complete context string with guidance, pages, and components
    """
    guidance = get_archetype_guidance(archetype)
    pages = get_archetype_pages(archetype)
    components = get_archetype_components(archetype)
    
    context = f"""
═══════════════════════════════════════════════════════
🎨 ARCHETYPE-SPECIFIC UI GUIDANCE
═══════════════════════════════════════════════════════

DETECTED ARCHETYPE: {archetype}
PRIMARY ENTITY: {entity}
DOMAIN: {domain}

{guidance}

📁 RECOMMENDED PAGES FOR THIS ARCHETYPE:
{chr(10).join(f"  - {page}" for page in pages)}

🧩 KEY COMPONENTS TO CREATE:
{chr(10).join(f"  - {comp}" for comp in components)}

⚠️ IMPORTANT: Do NOT just create a generic CRUD app!
Your UI must reflect the archetype's specific patterns and user experience.
For example:
- Admin Dashboard = Data tables + Stats cards + Charts
- E-commerce = Product grid + Cart + Filters
- Chat App = Message list + Channel sidebar + Presence indicators
- Project Management = Kanban board + Task cards

═══════════════════════════════════════════════════════
"""
    return context


# ═══════════════════════════════════════════════════════
# BACKEND API PATTERNS - Archetype-specific API structures
# ═══════════════════════════════════════════════════════

ARCHETYPE_BACKEND_GUIDANCE: Dict[str, Dict[str, str]] = {
    
    "admin_dashboard": {
        "description": "Admin API with aggregations and batch operations",
        "api_focus": """
🎯 ADMIN DASHBOARD API PATTERNS:

**BEYOND BASIC CRUD - Include these endpoints:**
```python
# Statistics endpoint
@router.get("/stats")
async def get_stats():
    total = await Entity.count()
    active = await Entity.find(Entity.status == "active").count()
    return {"total": total, "active": active, "growth": "+12.5%"}

# Bulk operations
@router.post("/bulk-delete")
async def bulk_delete(ids: List[PydanticObjectId]):
    result = await Entity.find(In(Entity.id, ids)).delete()
    return {"deleted": result.deleted_count}

# Advanced filtering
@router.get("/")
async def get_all(
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    order: str = "desc",
    skip: int = 0,
    limit: int = 20
):
    query = Entity.find()
    if status:
        query = query.find(Entity.status == status)
    if search:
        query = query.find({"$text": {"$search": search}})
    # Apply sorting and pagination
    ...
```

**MODEL ENHANCEMENTS:**
```python
class Entity(Document):
    name: str
    status: str = Field(default="active")  # For filtering
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None  # For audit trails
    
    class Settings:
        name = "entities"
        indexes = [
            IndexModel([("status", 1)]),  # For fast filtering
            IndexModel([("created_at", -1)]),  # For sorting
        ]
```
""",
    },
    
    "saas_app": {
        "description": "Multi-tenant API with auth and subscriptions",
        "api_focus": """
🎯 SAAS APPLICATION API PATTERNS:

**MULTI-TENANT AWARE ENDPOINTS:**
```python
# All queries scoped to tenant
@router.get("/")
async def get_all(current_user: User = Depends(get_current_user)):
    return await Entity.find(Entity.tenant_id == current_user.tenant_id).to_list()

# Team management
@router.post("/team/invite")
async def invite_member(email: str, role: str, current_user: User = Depends(get_current_user)):
    # Create invitation
    ...

# Subscription endpoints
@router.get("/subscription")
async def get_subscription(current_user: User = Depends(get_current_user)):
    return await Subscription.find_one(Subscription.tenant_id == current_user.tenant_id)
```

**MODEL PATTERNS:**
```python
class Entity(Document):
    tenant_id: PydanticObjectId  # Required for multi-tenancy
    created_by: PydanticObjectId
    # ... other fields

class User(Document):
    email: str
    tenant_id: PydanticObjectId
    role: str = Field(default="member")  # admin, member, viewer

class Subscription(Document):
    tenant_id: PydanticObjectId
    plan: str  # free, pro, enterprise
    status: str  # active, cancelled, past_due
    current_period_end: datetime
```
""",
    },
    
    "content_platform": {
        "description": "Content API with categories and publishing",
        "api_focus": """
🎯 CONTENT PLATFORM API PATTERNS:

**CONTENT-SPECIFIC ENDPOINTS:**
```python
# Get by category
@router.get("/category/{category}")
async def get_by_category(category: str, skip: int = 0, limit: int = 10):
    return await Article.find(Article.category == category).skip(skip).limit(limit).to_list()

# Publish/Unpublish
@router.post("/{id}/publish")
async def publish(id: PydanticObjectId):
    article = await Article.get(id)
    article.status = "published"
    article.published_at = datetime.now(timezone.utc)
    await article.save()
    return article

# Get by tag
@router.get("/tag/{tag}")
async def get_by_tag(tag: str):
    return await Article.find({"tags": tag}).to_list()
```

**MODEL PATTERNS:**
```python
class Article(Document):
    title: str
    slug: str  # URL-friendly identifier
    content: str
    excerpt: Optional[str] = None
    author_id: PydanticObjectId
    category: str
    tags: List[str] = Field(default_factory=list)
    status: str = Field(default="draft")  # draft, published, archived
    published_at: Optional[datetime] = None
    reading_time: Optional[int] = None  # in minutes
    
    class Settings:
        name = "articles"
        indexes = [
            IndexModel([("slug", 1)], unique=True),
            IndexModel([("category", 1)]),
            IndexModel([("tags", 1)]),
        ]
```
""",
    },
    
    "realtime_collab": {
        "description": "Real-time API with WebSocket support",
        "api_focus": """
🎯 REAL-TIME COLLABORATION API PATTERNS:

**WEBSOCKET + REST HYBRID:**
```python
from fastapi import WebSocket, WebSocketDisconnect

# Connection manager for WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)
    
    async def broadcast(self, channel: str, message: dict):
        for connection in self.active_connections.get(channel, []):
            await connection.send_json(message)

manager = ConnectionManager()

# WebSocket endpoint
@router.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    await manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_json()
            # Save message to DB
            msg = await Message.insert_one(Message(**data))
            # Broadcast to all clients
            await manager.broadcast(channel, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)

# REST endpoint to get message history
@router.get("/channels/{channel}/messages")
async def get_messages(channel: str, limit: int = 50):
    return await Message.find(Message.channel == channel).sort(-Message.timestamp).limit(limit).to_list()
```

**MODEL PATTERNS:**
```python
class Message(Document):
    channel: str
    sender_id: str
    sender_name: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
class Channel(Document):
    name: str
    members: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```
""",
    },
    
    "ecommerce_store": {
        "description": "E-commerce API with cart and checkout",
        "api_focus": """
🎯 E-COMMERCE API PATTERNS:

**SHOPPING CART ENDPOINTS:**
```python
# Get cart (session-based or user-based)
@router.get("/cart")
async def get_cart(session_id: str = Cookie(None)):
    cart = await Cart.find_one(Cart.session_id == session_id)
    if not cart:
        cart = Cart(session_id=session_id, items=[])
        await cart.insert()
    return cart

# Add to cart
@router.post("/cart/add")
async def add_to_cart(product_id: PydanticObjectId, quantity: int = 1, session_id: str = Cookie(None)):
    cart = await get_or_create_cart(session_id)
    # Check if product already in cart
    for item in cart.items:
        if item.product_id == product_id:
            item.quantity += quantity
            await cart.save()
            return cart
    # Add new item
    product = await Product.get(product_id)
    cart.items.append(CartItem(product_id=product_id, quantity=quantity, price=product.price))
    await cart.save()
    return cart

# Checkout
@router.post("/checkout")
async def checkout(session_id: str = Cookie(None)):
    cart = await Cart.find_one(Cart.session_id == session_id)
    # Create order
    order = Order(
        items=cart.items,
        total=sum(item.price * item.quantity for item in cart.items),
        status="pending"
    )
    await order.insert()
    # Clear cart
    cart.items = []
    await cart.save()
    return order
```

**MODEL PATTERNS:**
```python
class Product(Document):
    name: str
    description: str
    price: float
    original_price: Optional[float] = None  # For sale items
    category: str
    images: List[str] = Field(default_factory=list)
    in_stock: bool = True
    inventory_count: int = 0

class CartItem(BaseModel):
    product_id: PydanticObjectId
    quantity: int
    price: float

class Cart(Document):
    session_id: str
    items: List[CartItem] = Field(default_factory=list)
```
""",
    },
    
    "project_management": {
        "description": "Project API with board and task management",
        "api_focus": """
🎯 PROJECT MANAGEMENT API PATTERNS:

**KANBAN-STYLE ENDPOINTS:**
```python
# Get board with all columns and tasks
@router.get("/boards/{board_id}")
async def get_board(board_id: PydanticObjectId):
    board = await Board.get(board_id)
    columns = await Column.find(Column.board_id == board_id).sort(Column.position).to_list()
    for col in columns:
        col.tasks = await Task.find(Task.column_id == col.id).sort(Task.position).to_list()
    return {"board": board, "columns": columns}

# Move task between columns
@router.post("/tasks/{task_id}/move")
async def move_task(task_id: PydanticObjectId, to_column: PydanticObjectId, position: int):
    task = await Task.get(task_id)
    task.column_id = to_column
    task.position = position
    await task.save()
    # Reorder other tasks in column
    ...
    return task

# Update task status/assignee
@router.patch("/tasks/{task_id}")
async def update_task(task_id: PydanticObjectId, updates: TaskUpdate):
    task = await Task.get(task_id)
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    task.updated_at = datetime.now(timezone.utc)
    await task.save()
    return task
```

**MODEL PATTERNS:**
```python
class Task(Document):
    title: str
    description: Optional[str] = None
    column_id: PydanticObjectId
    board_id: PydanticObjectId
    assignee_id: Optional[PydanticObjectId] = None
    priority: str = Field(default="medium")  # low, medium, high, urgent
    due_date: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    position: int = 0  # For ordering within column
    subtasks: List[dict] = Field(default_factory=list)

class Column(Document):
    name: str
    board_id: PydanticObjectId
    position: int = 0
```
""",
    },
}


def get_backend_archetype_guidance(archetype: str) -> str:
    """
    Get backend API guidance for a specific archetype.
    
    Args:
        archetype: Project archetype (e.g., "admin_dashboard", "ecommerce_store")
        
    Returns:
        Formatted guidance string to inject into Derek's backend prompt
    """
    guidance = ARCHETYPE_BACKEND_GUIDANCE.get(archetype)
    
    if not guidance:
        return """
🎯 STANDARD CRUD API PATTERNS:

Create a clean REST API with:
- GET / - List all with pagination
- GET /{id} - Get single item
- POST / - Create new item  
- PUT /{id} - Update item
- DELETE /{id} - Delete item

🚨 ID PARAMETER HANDLING (CRITICAL):
ALWAYS use PydanticObjectId for ID parameters:
```python
from beanie import PydanticObjectId

@router.get("/{id}")
async def get_one(id: PydanticObjectId):
    item = await Entity.get(id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return item
```
This ensures invalid IDs return 422 (validation error) not 500 (server crash).
"""
    
    return guidance["api_focus"]


def get_full_backend_context(archetype: str, entity: str, domain: str) -> str:
    """
    Get complete archetype context for backend implementation.
    
    Args:
        archetype: Detected project archetype
        entity: Primary entity name
        domain: Business domain
        
    Returns:
        Complete context string with API patterns and model guidance
    """
    guidance = get_backend_archetype_guidance(archetype)
    
    return f"""
═══════════════════════════════════════════════════════
🔧 ARCHETYPE-SPECIFIC BACKEND GUIDANCE
═══════════════════════════════════════════════════════

DETECTED ARCHETYPE: {archetype}
PRIMARY ENTITY: {entity}
DOMAIN: {domain}

{guidance}

⚠️ IMPORTANT: Do NOT just create basic CRUD endpoints!
Your API must reflect the archetype's specific patterns:
- Admin Dashboard = Stats endpoints + Bulk operations + Advanced filtering
- E-commerce = Cart + Checkout + Inventory management
- Chat App = WebSocket + Message history + Presence
- Project Management = Board structure + Task movement + Status updates

═══════════════════════════════════════════════════════
"""


# ═══════════════════════════════════════════════════════
# ARCHITECTURE PATTERNS - Archetype-specific system design
# ═══════════════════════════════════════════════════════

ARCHETYPE_ARCHITECTURE_GUIDANCE: Dict[str, str] = {
    
    "admin_dashboard": """
## Architecture for Admin Dashboard

### Key Components
1. **Sidebar Navigation** - Collapsible with sections
2. **Data Tables** - With sorting, filtering, pagination
3. **Stats Cards** - KPI metrics at top of dashboard
4. **Charts** - Line/bar charts for trends (recharts)

### Recommended Folder Structure
```
frontend/src/
├── pages/
│   ├── DashboardPage.jsx    # Main dashboard with stats
│   ├── UsersPage.jsx        # User management table
│   └── SettingsPage.jsx     # App settings
├── components/
│   ├── Sidebar.jsx
│   ├── StatsCard.jsx
│   ├── DataTable.jsx
│   └── FilterBar.jsx
```

### API Design Focus
- Pagination on all list endpoints
- Filter/search query parameters
- Statistics/aggregation endpoints
- Bulk operation endpoints
""",
    
    "saas_app": """
## Architecture for SaaS Application

### Key Components
1. **Auth Flow** - Login/Signup/Forgot Password
2. **Multi-tenancy** - Team/organization isolation
3. **Subscription Management** - Plan tiers, billing
4. **Settings** - Profile, team, billing tabs

### Recommended Folder Structure
```
frontend/src/
├── pages/
│   ├── LandingPage.jsx      # Marketing page
│   ├── PricingPage.jsx      # Subscription tiers
│   ├── DashboardPage.jsx    # Main app
│   ├── TeamPage.jsx         # Team management
│   └── SettingsPage.jsx     # User settings
├── components/
│   ├── PricingCard.jsx
│   ├── TeamMemberRow.jsx
│   └── SettingsTabs.jsx
```

### API Design Focus
- Tenant-scoped queries
- Role-based access control
- Subscription status checks
""",
    
    "content_platform": """
## Architecture for Content Platform

### Key Components
1. **Article List** - Grid/list with filters
2. **Article Detail** - Full content with meta
3. **Category Navigation** - Tabs or sidebar
4. **Author Profiles** - Bylines with avatars

### Recommended Folder Structure
```
frontend/src/
├── pages/
│   ├── HomePage.jsx         # Featured + recent
│   ├── ArticlesPage.jsx     # All articles
│   ├── ArticleDetail.jsx    # Single article
│   └── CategoryPage.jsx     # By category
├── components/
│   ├── ArticleCard.jsx
│   ├── CategoryTabs.jsx
│   ├── AuthorByline.jsx
│   └── TagCloud.jsx
```

### API Design Focus
- Slug-based article retrieval
- Category/tag filtering
- Related articles endpoint
""",
    
    "realtime_collab": """
## Architecture for Real-time Collaboration

### Key Components
1. **Message List** - Chat bubbles with timestamps
2. **Channel Sidebar** - List of rooms/channels
3. **Presence Indicators** - Online/offline status
4. **Message Input** - With typing indicators

### Recommended Folder Structure
```
frontend/src/
├── pages/
│   ├── ChatPage.jsx         # Main chat interface
│   └── DirectMessagesPage.jsx
├── components/
│   ├── MessageBubble.jsx
│   ├── ChannelList.jsx
│   ├── PresenceIndicator.jsx
│   └── MessageInput.jsx
├── hooks/
│   └── useWebSocket.js      # WebSocket connection hook
```

### API Design Focus
- WebSocket for real-time messages
- REST for message history
- Presence/status endpoints
""",
    
    "ecommerce_store": """
## Architecture for E-commerce Store

### Key Components
1. **Product Grid** - Cards with images, prices
2. **Product Detail** - Gallery, variants, add to cart
3. **Shopping Cart** - Drawer/sidebar
4. **Checkout Flow** - Multi-step form

### Recommended Folder Structure
```
frontend/src/
├── pages/
│   ├── HomePage.jsx         # Featured products
│   ├── ProductsPage.jsx     # Product catalog
│   ├── ProductDetail.jsx    # Single product
│   ├── CartPage.jsx         # Shopping cart
│   └── CheckoutPage.jsx     # Checkout flow
├── components/
│   ├── ProductCard.jsx
│   ├── ProductGallery.jsx
│   ├── CartDrawer.jsx
│   ├── CartItem.jsx
│   └── ProductFilters.jsx
├── context/
│   └── CartContext.jsx      # Cart state management
```

### API Design Focus
- Cart management (session-based)
- Product filtering/search
- Inventory availability
- Order creation
""",
    
    "project_management": """
## Architecture for Project Management

### Key Components
1. **Kanban Board** - Draggable columns and cards
2. **Task Cards** - Compact with key info
3. **Task Detail Modal** - Full task editing
4. **Project Sidebar** - Workspace/project list

### Recommended Folder Structure
```
frontend/src/
├── pages/
│   ├── BoardPage.jsx        # Kanban board
│   ├── TimelinePage.jsx     # Gantt-style view
│   └── CalendarPage.jsx     # Calendar view
├── components/
│   ├── KanbanColumn.jsx
│   ├── TaskCard.jsx
│   ├── TaskModal.jsx
│   ├── ProjectSidebar.jsx
│   └── AssigneeAvatar.jsx
├── context/
│   └── BoardContext.jsx     # Board state
```

### API Design Focus
- Board with nested columns/tasks
- Task movement between columns
- Bulk task updates
- Activity/history tracking
""",
}


def get_architecture_archetype_guidance(archetype: str, ui_vibe: str) -> str:
    """
    Get architecture guidance for a specific archetype.
    
    Args:
        archetype: Project archetype
        ui_vibe: UI aesthetic vibe
        
    Returns:
        Architecture guidance to inject into Victoria's prompt
    """
    guidance = ARCHETYPE_ARCHITECTURE_GUIDANCE.get(archetype, "")
    
    if not guidance:
        guidance = """
## General Application Architecture

### Standard Folder Structure
```
frontend/src/
├── pages/          # Route components
├── components/     # Reusable UI components
├── lib/            # Utilities and API client
└── data/           # Mock data
```
"""
    
    return f"""
═══════════════════════════════════════════════════════
🏗️ ARCHETYPE-SPECIFIC ARCHITECTURE GUIDANCE
═══════════════════════════════════════════════════════

ARCHETYPE: {archetype}
UI VIBE: {ui_vibe}

{guidance}

⚠️ Your architecture MUST reflect this archetype's patterns!
Do NOT create a generic CRUD architecture for every project.

═══════════════════════════════════════════════════════
"""


# ═══════════════════════════════════════════════════════
# PATTERN STORE INTEGRATION - Learning from pre-training
# ═══════════════════════════════════════════════════════

def get_archetype_patterns_from_store(archetype: str, step: str) -> str:
    """
    Retrieve learned patterns from PatternStore for this archetype.
    
    This integrates with the pre-training data to provide
    archetype-specific code examples from successful builds.
    
    Args:
        archetype: Project archetype
        step: Workflow step (frontend_mock, backend_implementation, etc.)
        
    Returns:
        Pattern hints string to inject into prompts
    """
    try:
        from app.learning.pattern_store import get_pattern_store
        
        store = get_pattern_store()
        patterns = store.retrieve_patterns(archetype, step, min_quality=7.0, limit=3)
        
        if not patterns:
            return ""
        
        hints = f"""
═══════════════════════════════════════════════════════
🧠 LEARNED PATTERNS FROM SIMILAR PROJECTS
═══════════════════════════════════════════════════════

Found {len(patterns)} successful pattern(s) for "{archetype}" / "{step}":

"""
        for i, pattern in enumerate(patterns, 1):
            hints += f"""
Pattern {i} (Quality: {pattern.quality_score}/10, Used: {pattern.success_count}x):
"""
            for fp in pattern.file_patterns[:3]:
                has_testid = "✅" if fp.get("has_testid") else ""
                hints += f"  - {fp['path']} (~{fp['size']} bytes) {has_testid}\n"
            
            if pattern.file_patterns and pattern.file_patterns[0].get("imports"):
                imports = pattern.file_patterns[0]["imports"][:5]
                hints += f"  Imports: {', '.join(imports)}\n"
        
        hints += """
Follow these proven patterns for best results!
═══════════════════════════════════════════════════════
"""
        return hints
        
    except Exception:
        # Fail silently - patterns are enhancement, not required
        return ""


def get_enhanced_prompt_context(
    archetype: str,
    entity: str,
    domain: str,
    step: str,
    ui_vibe: str = ""
) -> str:
    """
    Get complete enhanced context for any step.
    
    Combines:
    1. Static archetype guidance
    2. Learned patterns from PatternStore
    
    Args:
        archetype: Project archetype
        entity: Primary entity
        domain: Business domain
        step: Workflow step
        ui_vibe: UI aesthetic (optional)
        
    Returns:
        Complete enhanced prompt context
    """
    context_parts = []
    
    # Add step-specific archetype guidance
    if step in ["frontend_mock", "frontend_integration"]:
        context_parts.append(get_full_archetype_context(archetype, entity, domain))
    elif step in ["backend_implementation", "backend_models", "backend_routers"]:
        context_parts.append(get_full_backend_context(archetype, entity, domain))
    elif step == "architecture":
        context_parts.append(get_architecture_archetype_guidance(archetype, ui_vibe))
    elif step in ["testing_frontend", "e2e_tests"]:
        context_parts.append(get_e2e_testing_guidance(archetype, entity))
    
    # Add learned patterns (if available)
    pattern_hints = get_archetype_patterns_from_store(archetype, step)
    if pattern_hints:
        context_parts.append(pattern_hints)
    
    return "\n\n".join(context_parts)


# ═══════════════════════════════════════════════════════
# E2E TESTING PATTERNS - Archetype-specific test scenarios
# ═══════════════════════════════════════════════════════

ARCHETYPE_E2E_TESTING_GUIDANCE: Dict[str, str] = {
    
    "admin_dashboard": """
🧪 ADMIN DASHBOARD E2E TEST PATTERNS:

**KEY SCENARIOS TO TEST:**
1. Dashboard loads with stats cards visible
2. Data table displays items with columns
3. Filter/search functionality works
4. Pagination controls navigate correctly
5. Status badges show correct colors

**EXAMPLE TESTS:**
```javascript
test('dashboard shows statistics cards', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Stats cards should be visible
  await expect(page.locator('[data-testid="stats-card"]').first()).toBeVisible();
  // Or by heading
  await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
});

test('data table displays items', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Wait for table to load
  await expect(page.locator('table').or(page.locator('[data-testid="data-table"]'))).toBeVisible();
  
  // Should have rows
  const rows = page.locator('tbody tr').or(page.locator('[data-testid="table-row"]'));
  await expect(rows.first()).toBeVisible();
});

test('search filters the table', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  const searchInput = page.getByPlaceholder(/search/i)
    .or(page.locator('[data-testid="search-input"]'));
  await searchInput.fill('test');
  
  // Table should update (either fewer rows or "no results")
  await page.waitForTimeout(500); // debounce
});
```
""",
    
    "saas_app": """
🧪 SAAS APPLICATION E2E TEST PATTERNS:

**KEY SCENARIOS TO TEST:**
1. Landing page loads with hero section
2. Pricing cards display correctly
3. Feature list is visible
4. Navigation links work
5. CTA buttons are clickable

**EXAMPLE TESTS:**
```javascript
test('landing page shows hero section', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Hero headline
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  
  // CTA button
  await expect(page.getByRole('button', { name: /get started|sign up|try/i })).toBeVisible();
});

test('pricing section displays plans', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Scroll to pricing or navigate
  const pricingSection = page.locator('[data-testid="pricing"]')
    .or(page.getByRole('region', { name: /pricing/i }));
  
  // Multiple pricing cards
  const cards = page.locator('[data-testid="pricing-card"]')
    .or(page.locator('.pricing-card'));
  await expect(cards.first()).toBeVisible();
});

test('navigation links work', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Click on Features link
  await page.getByRole('link', { name: /features/i }).click();
  await expect(page.url()).toContain('features');
});
```
""",
    
    "content_platform": """
🧪 CONTENT PLATFORM E2E TEST PATTERNS:

**KEY SCENARIOS TO TEST:**
1. Article list/grid displays
2. Article cards show title, excerpt, author
3. Category tabs filter content
4. Clicking article navigates to detail
5. Tags are visible

**EXAMPLE TESTS:**
```javascript
test('article list displays cards', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Article cards
  const cards = page.locator('[data-testid="article-card"]')
    .or(page.locator('article'));
  await expect(cards.first()).toBeVisible();
  
  // Card should have title
  await expect(cards.first().getByRole('heading')).toBeVisible();
});

test('category tabs filter articles', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Find category tabs
  const tabs = page.getByRole('tab').or(page.locator('[data-testid="category-tab"]'));
  
  // Click a category
  await tabs.nth(1).click();
  
  // Content should update
  await page.waitForTimeout(300);
});

test('clicking article shows detail', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Click first article
  const firstCard = page.locator('[data-testid="article-card"]').first()
    .or(page.locator('article').first());
  await firstCard.click();
  
  // Should show article content
  await expect(page.getByRole('article').or(page.locator('[data-testid="article-content"]'))).toBeVisible();
});
```
""",
    
    "realtime_collab": """
🧪 REAL-TIME COLLABORATION E2E TEST PATTERNS:

**KEY SCENARIOS TO TEST:**
1. Chat interface loads
2. Channel list is visible
3. Message input is present
4. Messages display in list
5. Send button works (mock)

**EXAMPLE TESTS:**
```javascript
test('chat interface loads', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Main chat layout
  await expect(page.locator('[data-testid="chat-container"]')
    .or(page.locator('.chat-layout'))).toBeVisible();
});

test('channel sidebar shows channels', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Channel list
  const channels = page.locator('[data-testid="channel-list"]')
    .or(page.locator('.channel-list'));
  await expect(channels).toBeVisible();
  
  // Should have at least one channel
  const channelItems = page.locator('[data-testid="channel-item"]')
    .or(channels.locator('li, button'));
  await expect(channelItems.first()).toBeVisible();
});

test('message input is functional', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Message input
  const input = page.getByPlaceholder(/message|type/i)
    .or(page.locator('[data-testid="message-input"]'));
  await expect(input).toBeVisible();
  
  // Type a message
  await input.fill('Hello, world!');
  
  // Send button
  const sendBtn = page.getByRole('button', { name: /send/i })
    .or(page.locator('[data-testid="send-button"]'));
  await expect(sendBtn).toBeEnabled();
});

test('messages display in list', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Message list
  const messageList = page.locator('[data-testid="message-list"]')
    .or(page.locator('.messages'));
  await expect(messageList).toBeVisible();
});
```
""",
    
    "ecommerce_store": """
🧪 E-COMMERCE STORE E2E TEST PATTERNS:

**KEY SCENARIOS TO TEST:**
1. Product grid displays items
2. Product cards show image, price, title
3. Add to Cart button works
4. Cart icon updates count
5. Filter sidebar works

**EXAMPLE TESTS:**
```javascript
test('product grid displays items', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Product grid
  const products = page.locator('[data-testid="product-card"]')
    .or(page.locator('.product-card'));
  await expect(products.first()).toBeVisible();
  
  // Should have multiple products
  await expect(products).toHaveCount(await products.count()); // at least 1
});

test('product card shows price', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  const firstProduct = page.locator('[data-testid="product-card"]').first()
    .or(page.locator('.product-card').first());
  
  // Price should be visible
  await expect(firstProduct.locator('[data-testid="product-price"]')
    .or(firstProduct.locator('.price'))).toBeVisible();
});

test('add to cart button is clickable', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Find Add to Cart button
  const addToCartBtn = page.getByRole('button', { name: /add to cart|add/i }).first()
    .or(page.locator('[data-testid="add-to-cart"]').first());
  await expect(addToCartBtn).toBeVisible();
  
  // Click it
  await addToCartBtn.click();
  
  // Cart count should update or toast should appear
  await page.waitForTimeout(300);
});

test('cart icon shows count', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Cart icon
  const cartIcon = page.locator('[data-testid="cart-icon"]')
    .or(page.getByRole('button', { name: /cart/i }));
  await expect(cartIcon).toBeVisible();
});

test('category filter updates products', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Find category filter
  const categoryFilter = page.locator('[data-testid="category-filter"]')
    .or(page.getByRole('button', { name: /category|filter/i }));
  
  if (await categoryFilter.isVisible()) {
    await categoryFilter.click();
    await page.waitForTimeout(300);
  }
});
```
""",
    
    "project_management": """
🧪 PROJECT MANAGEMENT E2E TEST PATTERNS:

**KEY SCENARIOS TO TEST:**
1. Kanban board displays columns
2. Task cards are visible in columns
3. Add Task button works
4. Task card shows title, assignee
5. Column headers show count

**EXAMPLE TESTS:**
```javascript
test('kanban board shows columns', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Kanban columns
  const columns = page.locator('[data-testid="kanban-column"]')
    .or(page.locator('.kanban-column'));
  await expect(columns.first()).toBeVisible();
  
  // Should have multiple columns (To Do, In Progress, Done)
  await expect(columns).toHaveCount(await columns.count()); // at least 1
});

test('columns contain task cards', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Task cards
  const tasks = page.locator('[data-testid="task-card"]')
    .or(page.locator('.task-card'));
  await expect(tasks.first()).toBeVisible();
});

test('add task button opens dialog', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Add Task button
  const addBtn = page.getByRole('button', { name: /add task|new task|\+ add/i })
    .or(page.locator('[data-testid="add-task-btn"]'));
  await expect(addBtn).toBeVisible();
  
  await addBtn.click();
  
  // Dialog or form should appear
  await expect(page.getByRole('dialog')
    .or(page.locator('[data-testid="task-form"]'))).toBeVisible();
});

test('task card shows title', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  const firstTask = page.locator('[data-testid="task-card"]').first()
    .or(page.locator('.task-card').first());
  
  // Task title
  await expect(firstTask.getByRole('heading')
    .or(firstTask.locator('.task-title'))).toBeVisible();
});

test('column headers show task count', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Column header should show count
  const columnHeader = page.locator('[data-testid="column-header"]').first()
    .or(page.locator('.column-header').first());
  await expect(columnHeader).toBeVisible();
});
```
""",
    
    "landing_page": """
🧪 LANDING PAGE E2E TEST PATTERNS:

**KEY SCENARIOS TO TEST:**
1. Hero section displays with headline
2. Feature grid shows icons and text
3. CTA buttons are visible
4. Navigation works
5. Footer links present

**EXAMPLE TESTS:**
```javascript
test('hero section displays', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Main headline
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  
  // Subheadline
  await expect(page.locator('p').first()).toBeVisible();
});

test('CTA buttons are clickable', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Primary CTA
  const primaryCTA = page.getByRole('button', { name: /get started|try free|sign up/i })
    .or(page.locator('[data-testid="primary-cta"]'));
  await expect(primaryCTA).toBeVisible();
  await expect(primaryCTA).toBeEnabled();
});

test('feature section shows cards', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Feature cards
  const features = page.locator('[data-testid="feature-card"]')
    .or(page.locator('.feature-card'));
  await expect(features.first()).toBeVisible();
});

test('navigation links work', async ({ page }) => {
  await page.goto('http://localhost:5174/');
  
  // Nav should be visible
  const nav = page.getByRole('navigation');
  await expect(nav).toBeVisible();
  
  // Links should be present
  await expect(page.getByRole('link').first()).toBeVisible();
});
```
""",
}


def get_e2e_testing_guidance(archetype: str, entity: str) -> str:
    """
    Get E2E testing guidance for a specific archetype.
    
    Args:
        archetype: Project archetype
        entity: Primary entity name
        
    Returns:
        E2E testing guidance to inject into Luna's prompt
    """
    guidance = ARCHETYPE_E2E_TESTING_GUIDANCE.get(archetype, "")
    
    if not guidance:
        guidance = """
🧪 GENERAL E2E TEST PATTERNS:

**STANDARD TESTS:**
1. Page loads without crashing
2. Main heading is visible
3. Primary content displays
4. Buttons are clickable
5. Navigation works
"""
    
    return f"""
═══════════════════════════════════════════════════════
🧪 ARCHETYPE-SPECIFIC E2E TESTING GUIDANCE
═══════════════════════════════════════════════════════

ARCHETYPE: {archetype}
PRIMARY ENTITY: {entity}

{guidance}

⚠️ IMPORTANT:
- Use data-testid selectors when available
- Use role-based selectors as fallback (getByRole)
- Always use full URL: page.goto('http://localhost:5174/')
- Handle loading states with appropriate timeouts
- Test actual app functionality, not generic patterns

═══════════════════════════════════════════════════════
"""

