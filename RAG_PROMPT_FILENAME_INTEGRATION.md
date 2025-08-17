# RAG Integration with Prompt Filename Differentiation

## 🎯 **Overview**

This document summarizes the **deep integration of RAG functionality with prompt filename differentiation** in the Outline Chapter Strategy. The system now automatically creates separate RAG story contexts for each prompt filename, ensuring complete story isolation and preventing cross-contamination between different stories.

## 🏗️ **Architecture Changes**

### **1. Strategy Constructor Enhancement**

**File**: `src/application/strategies/outline_chapter/strategy.py`

**Changes**:
- Added `self._prompt_filename` attribute to track the current prompt filename
- Added `self._rag_story_id` attribute to track the current RAG story
- Integrated RAG story initialization with existing savepoint workflow
- Automatic RAG story creation when savepoints are set up

**Key Integration Point**:
```python
def _setup_savepoints(self, prompt_filename: str) -> None:
    # ... existing savepoint setup ...
    
    # Store the prompt filename for RAG context
    self._prompt_filename = prompt_filename
    
    # Initialize RAG story context for this prompt filename
    if self.rag_service:
        asyncio.create_task(self._initialize_rag_story(prompt_filename))
```

### **2. RAG Story Initialization**

**Automatic Story Creation**:
```python
async def _initialize_rag_story(self, prompt_filename: str) -> None:
    """Initialize RAG story context for the given prompt filename."""
    try:
        if not self.rag_service:
            return
        
        # Create or get story in RAG system using prompt filename as identifier
        story_id = await self.rag_service.create_story(
            story_name=prompt_filename,
            prompt_file_path=prompt_filename
        )
        
        # Store the story ID for future use
        self._rag_story_id = story_id
        
        print(f"✅ RAG story initialized for '{prompt_filename}' with ID: {story_id}")
        
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize RAG story for '{prompt_filename}': {e}")
```

### **3. OutlineGenerator Enhancement**

**File**: `src/application/strategies/outline_chapter/outline_generator.py`

**Changes**:
- Added `rag_service` parameter to constructor for RAG integration service
- **No prompt filename tracking** - this is managed by the strategy
- **No RAG story ID tracking** - this is managed by the strategy
- Focuses on its core responsibility: outline generation

**Constructor**:
```python
def __init__(
    self,
    model_provider: ModelProvider,
    config: Dict[str, Any],
    prompt_handler: PromptHandler,
    system_message: str,
    savepoint_manager: Optional[SavepointManager] = None,
    rag_service: Optional[RAGService] = None  # For RAG integration service only
):
    # ... existing initialization ...
    # No prompt_filename or _rag_story_id attributes
```

**Key Principle**: The outline generator focuses on outline generation and RAG integration services, while the strategy manages story context and prompt filename tracking.

## 🔄 **Workflow Integration**

### **1. Automatic RAG Story Creation**

**Flow**:
1. **Strategy Creation** → RAG service injected (optional)
2. **Savepoint Setup** → `_setup_savepoints(prompt_filename)` called
3. **Context Storage** → Prompt filename stored in strategy
4. **RAG Initialization** → `_initialize_rag_story(prompt_filename)` triggered
5. **Story Creation** → RAG service creates story with prompt filename as identifier
6. **ID Storage** → Story ID stored in strategy

### **2. Prompt Filename as Story Identifier**

**Key Principle**: Each unique prompt filename gets its own RAG story context
- `story_1.txt` → RAG Story ID 1
- `story_2.txt` → RAG Story ID 2
- `adventure_story.txt` → RAG Story ID 3
- `mystery_story.txt` → RAG Story ID 4

### **3. Seamless Integration with Savepoints**

**Existing Workflow Preserved**:
- Savepoint setup continues to work as before
- RAG story initialization happens automatically
- No breaking changes to existing functionality
- RAG integration is completely transparent

## 📊 **RAG Status and Monitoring**

### **1. Comprehensive Status Information**

```python
def get_rag_status(self) -> Dict[str, Any]:
    """Get comprehensive RAG status including story information."""
    status = {
        "rag_service_available": self.rag_service is not None,
        "prompt_filename": self._prompt_filename,
        "rag_story_active": self.has_rag_story(),
        "rag_story_id": self._rag_story_id
    }
    
    if self.rag_service:
        status["rag_service_type"] = type(self.rag_service).__name__
    
    return status
```

**Note**: The strategy only reports on its own RAG capabilities and state. It does not inspect or report on the outline generator's internal RAG integration state, maintaining clean separation of concerns.

### **2. Story State Checking**

```python
def has_rag_story(self) -> bool:
    """Check if a RAG story is currently active."""
    return self._rag_story_id is not None

def get_rag_story_id(self) -> Optional[int]:
    """Get the current RAG story ID for the active prompt filename."""
    return self._rag_story_id

def get_current_prompt_filename(self) -> Optional[str]:
    """Get the current prompt filename for the active story."""
    return self._prompt_filename
```

## 🎯 **Architecture Benefits**

### **1. Proper Separation of Concerns**
- **Strategy**: Manages story context, prompt filenames, and RAG story IDs
- **OutlineGenerator**: Focuses on outline generation and RAG integration services
- **No circular dependencies**: Strategy doesn't call outline generator methods to set state

### **2. Clean Dependency Direction**
- **Strategy** → **OutlineGenerator**: Strategy creates and configures outline generator
- **OutlineGenerator** → **Strategy**: Outline generator can access strategy methods when needed
- **No reverse dependencies**: Outline generator doesn't manage strategy state

### **3. Maintainable Design**
- **Single source of truth**: Prompt filename and RAG story ID stored only in strategy
- **Clear responsibilities**: Each component has well-defined roles
- **Easy testing**: Mock objects can focus on their specific responsibilities

## 🧪 **Testing and Verification**

### **1. Test Script**: `test_rag_integration.py`

**Tests**:
- Strategy creation with and without RAG service
- Prompt filename differentiation
- RAG story isolation
- Story ID propagation
- Status verification

### **2. Demo Script**: `demo_rag_integration.py`

**Demonstrates**:
- RAG service injection
- Automatic story creation
- Prompt filename differentiation
- Story isolation verification
- Integration benefits

## 🎯 **Key Benefits**

### **1. Automatic Story Isolation**
- **No manual configuration** required
- **Each prompt filename** gets its own RAG context
- **Complete separation** between different stories
- **No cross-contamination** of story content

### **2. Seamless Integration**
- **Leverages existing** savepoint workflow
- **No breaking changes** to current functionality
- **Transparent operation** - works with or without RAG
- **Automatic initialization** when RAG service is available

### **3. Robust Story Management**
- **Unique story IDs** for each prompt filename
- **Automatic cleanup** and isolation
- **Error handling** for RAG operations
- **Status monitoring** and verification

### **4. Foundation for Future Features**
- **RAG context retrieval** methods can now use story ID
- **Content indexing** can be scoped to specific stories
- **Story-aware operations** can leverage prompt filename context
- **Advanced RAG features** can build on this foundation

## 🔧 **Usage Examples**

### **1. Basic Usage**

```python
# Create strategy with RAG service
strategy = OutlineChapterStrategy(
    model_provider=model_provider,
    config=config,
    prompt_loader=prompt_loader,
    savepoint_repo=savepoint_repo,
    rag_service=rag_service  # RAG service injected
)

# Generate outline - RAG story automatically initialized
outline = await strategy.generate_outline(
    prompt="Write a story about...",
    settings=settings,
    prompt_filename="my_story.txt"  # Triggers RAG story creation
)
```

### **2. RAG Status Checking**

```python
# Check RAG status
status = strategy.get_rag_status()
if status["rag_story_active"]:
    print(f"RAG story active: {status['rag_story_id']}")
    print(f"Prompt filename: {status['prompt_filename']}")
```

### **3. Story ID Access**

```python
# Get current RAG story ID
story_id = strategy.get_rag_story_id()
if story_id:
    print(f"Current RAG story ID: {story_id}")

# Get current prompt filename
filename = strategy.get_current_prompt_filename()
if filename:
    print(f"Current prompt filename: {filename}")
```

## 🚧 **Implementation Considerations**

### **1. Asynchronous Operations**
- RAG story initialization is asynchronous
- Uses `asyncio.create_task()` for non-blocking operation
- Error handling prevents initialization failures from breaking workflow

### **2. Error Handling**
- Graceful degradation when RAG service is unavailable
- Warning messages for RAG initialization failures
- No breaking changes to existing functionality

### **3. Performance**
- RAG story initialization happens in background
- No blocking operations during savepoint setup
- Efficient story ID tracking and propagation

## 🔮 **Future Enhancements**

### **1. Content Indexing**
- Automatic indexing of generated content to RAG stories
- Story-scoped content retrieval and search
- Character and setting context preservation

### **2. Context Enhancement**
- RAG context integration in outline generation
- Historical story pattern recognition
- Character and world consistency maintenance

### **3. Advanced Features**
- Cross-story similarity detection
- Story pattern learning and adaptation
- Advanced context selection and filtering

## 📝 **Summary**

This implementation provides **deep, automatic integration** of RAG functionality with prompt filename differentiation while maintaining proper architectural principles:

- ✅ **Automatic RAG story creation** per prompt filename
- ✅ **Complete story isolation** and context separation
- ✅ **Seamless integration** with existing savepoint workflow
- ✅ **Transparent operation** with comprehensive status monitoring
- ✅ **Foundation for advanced** RAG features and content management
- ✅ **Proper separation of concerns** between strategy and outline generator
- ✅ **No circular dependencies** or architectural antipatterns

The system now automatically assumes that every story has a prompt filename and creates isolated RAG contexts accordingly, ensuring that all RAG storage and operations are properly differentiated by story. The architecture maintains clean dependency direction with the strategy managing story context and the outline generator focusing on its core responsibilities.
