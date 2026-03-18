# Spring WebMVC

## Controller Patterns

### REST Controller

```kotlin
@RestController
@RequestMapping("/api/v1/users")
class UserController(
    private val userService: UserService
) {
    @GetMapping("/{id}")
    fun getUser(@PathVariable id: Long): ResponseEntity<UserResponse> {
        return userService.findById(id)
            ?.let { ResponseEntity.ok(it) }
            ?: ResponseEntity.notFound().build()
    }

    @GetMapping
    fun listUsers(
        @RequestParam(required = false) status: UserStatus?,
        @PageableDefault(size = 20) pageable: Pageable
    ): Page<UserResponse> =
        userService.findAll(status, pageable)

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    fun createUser(
        @Valid @RequestBody request: CreateUserRequest
    ): UserResponse =
        userService.create(request)

    @PutMapping("/{id}")
    fun updateUser(
        @PathVariable id: Long,
        @Valid @RequestBody request: UpdateUserRequest
    ): UserResponse =
        userService.update(id, request)

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    fun deleteUser(@PathVariable id: Long) {
        userService.delete(id)
    }
}
```

### Request Binding

```kotlin
data class SearchRequest(
    @field:NotBlank
    val keyword: String,

    @field:Min(0)
    val minAge: Int? = null,

    @field:Max(150)
    val maxAge: Int? = null,

    @field:Pattern(regexp = "^[A-Z]{2}$")
    val country: String? = null
)

@GetMapping("/search")
fun search(@Valid @ModelAttribute request: SearchRequest): List<UserResponse> =
    userService.search(request)
```

### Path Variables and Query Parameters

```kotlin
// Path variable with regex constraint
@GetMapping("/users/{id:\\d+}")
fun getUserById(@PathVariable id: Long): UserResponse

// Multiple path variables
@GetMapping("/users/{userId}/orders/{orderId}")
fun getOrder(
    @PathVariable userId: Long,
    @PathVariable orderId: Long
): OrderResponse

// Optional query parameter
@GetMapping("/products")
fun listProducts(
    @RequestParam(required = false, defaultValue = "10") limit: Int,
    @RequestParam(required = false) category: String?
): List<ProductResponse>

// Collection query parameter
@GetMapping("/users")
fun getUsersByIds(
    @RequestParam("id") ids: List<Long>
): List<UserResponse>
```

## Exception Handling

### Global Exception Handler

```kotlin
@RestControllerAdvice
class GlobalExceptionHandler {

    @ExceptionHandler(EntityNotFoundException::class)
    fun handleNotFound(e: EntityNotFoundException): ResponseEntity<ErrorResponse> =
        ResponseEntity
            .status(HttpStatus.NOT_FOUND)
            .body(ErrorResponse(
                code = "ENTITY_NOT_FOUND",
                message = e.message ?: "Entity not found"
            ))

    @ExceptionHandler(BusinessException::class)
    fun handleBusinessException(e: BusinessException): ResponseEntity<ErrorResponse> =
        ResponseEntity
            .status(e.errorCode.status)
            .body(ErrorResponse(
                code = e.errorCode.code,
                message = e.message
            ))

    @ExceptionHandler(MethodArgumentNotValidException::class)
    fun handleValidation(e: MethodArgumentNotValidException): ResponseEntity<ErrorResponse> {
        val errors = e.bindingResult.fieldErrors.map { fieldError ->
            FieldError(fieldError.field, fieldError.defaultMessage ?: "Invalid")
        }
        return ResponseEntity
            .status(HttpStatus.BAD_REQUEST)
            .body(ErrorResponse(
                code = "VALIDATION_ERROR",
                message = "Validation failed",
                details = errors
            ))
    }

    @ExceptionHandler(HttpMediaTypeNotSupportedException::class)
    fun handleMediaType(e: HttpMediaTypeNotSupportedException): ResponseEntity<ErrorResponse> =
        ResponseEntity
            .status(HttpStatus.UNSUPPORTED_MEDIA_TYPE)
            .body(ErrorResponse(
                code = "UNSUPPORTED_MEDIA_TYPE",
                message = "Content type ${e.contentType} is not supported"
            ))

    @ExceptionHandler(Exception::class)
    fun handleUnexpected(e: Exception): ResponseEntity<ErrorResponse> {
        log.error("Unexpected error", e)
        return ResponseEntity
            .status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(ErrorResponse(
                code = "INTERNAL_ERROR",
                message = "An unexpected error occurred"
            ))
    }
}
```

### Custom Error Response

```kotlin
data class ErrorResponse(
    val code: String,
    val message: String,
    val timestamp: Instant = Instant.now(),
    val details: Any? = null
)

data class FieldError(
    val field: String,
    val message: String
)

enum class ErrorCode(
    val code: String,
    val status: HttpStatus
) {
    ENTITY_NOT_FOUND("ENTITY_NOT_FOUND", HttpStatus.NOT_FOUND),
    DUPLICATE_EMAIL("DUPLICATE_EMAIL", HttpStatus.CONFLICT),
    UNAUTHORIZED("UNAUTHORIZED", HttpStatus.UNAUTHORIZED),
    FORBIDDEN("FORBIDDEN", HttpStatus.FORBIDDEN),
    VALIDATION_ERROR("VALIDATION_ERROR", HttpStatus.BAD_REQUEST)
}
```

## Filter vs Interceptor

### Filter (Servlet Level)

```kotlin
@Component
class RequestLoggingFilter : OncePerRequestFilter() {

    override fun doFilterInternal(
        request: HttpServletRequest,
        response: HttpServletResponse,
        filterChain: FilterChain
    ) {
        val startTime = System.currentTimeMillis()

        // Before request
        log.info("Request: ${request.method} ${request.requestURI}")

        filterChain.doFilter(request, response)

        // After request
        val duration = System.currentTimeMillis() - startTime
        log.info("Response: ${response.status} (${duration}ms)")
    }
}
```

### Interceptor (Spring MVC Level)

```kotlin
@Component
class AuthenticationInterceptor : HandlerInterceptor {

    override fun preHandle(
        request: HttpServletRequest,
        response: HttpServletResponse,
        handler: Any
    ): Boolean {
        val token = request.getHeader("Authorization")
            ?: run {
                response.sendError(HttpStatus.UNAUTHORIZED.value(), "Missing token")
                return false
            }

        val user = authService.validateToken(token)
            ?: run {
                response.sendError(HttpStatus.UNAUTHORIZED.value(), "Invalid token")
                return false
            }

        request.setAttribute("currentUser", user)
        return true
    }

    override fun afterCompletion(
        request: HttpServletRequest,
        response: HttpServletResponse,
        handler: Any,
        ex: Exception?
    ) {
        // Cleanup or logging
    }
}

@Configuration
class WebConfig : WebMvcConfigurer {

    override fun addInterceptors(registry: InterceptorRegistry) {
        registry.addInterceptor(authenticationInterceptor)
            .addPathPatterns("/api/**")
            .excludePathPatterns(
                "/api/auth/login",
                "/api/auth/refresh",
                "/api/health"
            )
    }
}
```

### When to Use What

| Use Case | Filter | Interceptor |
|----------|--------|-------------|
| Authentication/Authorization | ✅ | ✅ |
| CORS | ✅ | |
| Request logging | ✅ | ✅ |
| Request timing | | ✅ |
| Handler-specific logic | | ✅ |
| Modify request/response body | ✅ | |

## CORS Configuration

```kotlin
@Configuration
class CorsConfig : WebMvcConfigurer {

    override fun addCorsMappings(registry: CorsRegistry) {
        registry.addMapping("/api/**")
            .allowedOrigins(
                "https://app.example.com",
                "https://admin.example.com"
            )
            .allowedMethods("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS")
            .allowedHeaders("*")
            .allowCredentials(true)
            .maxAge(3600)
    }
}

// Or per-controller
@RestController
@CrossOrigin(
    origins = ["https://app.example.com"],
    methods = [RequestMethod.GET, RequestMethod.POST],
    maxAge = 3600
)
class UserController
```

## File Upload

### Multipart File Upload

```kotlin
@PostMapping("/upload", consumes = [MediaType.MULTIPART_FORM_DATA_VALUE])
fun uploadFile(
    @RequestPart("file") file: MultipartFile,
    @RequestPart("metadata") metadata: UploadMetadata
): UploadResponse {
    if (file.isEmpty) {
        throw BusinessException("File is empty")
    }

    val savedPath = fileStorageService.store(file)
    return UploadResponse(savedPath, file.originalFilename, file.size)
}

@PostMapping("/upload/multiple")
fun uploadFiles(
    @RequestPart("files") files: List<MultipartFile>
): List<UploadResponse> {
    return files.map { file ->
        val savedPath = fileStorageService.store(file)
        UploadResponse(savedPath, file.originalFilename, file.size)
    }
}
```

### File Download

```kotlin
@GetMapping("/download/{filename}")
fun downloadFile(
    @PathVariable filename: String
): ResponseEntity<Resource> {
    val resource = fileStorageService.loadAsResource(filename)
    return ResponseEntity.ok()
        .contentType(MediaType.APPLICATION_OCTET_STREAM)
        .header(
            HttpHeaders.CONTENT_DISPOSITION,
            "attachment; filename=\"${resource.filename}\""
        )
        .body(resource)
}
```

## ResponseEntity Patterns

### Builder Pattern

```kotlin
@GetMapping("/{id}")
fun getUser(@PathVariable id: Long): ResponseEntity<UserResponse> {
    val user = userService.findById(id)
        ?: return ResponseEntity.notFound().build()

    return ResponseEntity.ok()
        .header("X-Custom-Header", "value")
        .eTag("\"${user.version}\"")
        .lastModified(user.updatedAt.toEpochMilli())
        .body(user)
}

@PostMapping
fun createUser(@RequestBody request: CreateUserRequest): ResponseEntity<UserResponse> {
    val user = userService.create(request)
    return ResponseEntity
        .created(URI.create("/api/v1/users/${user.id}"))
        .body(user)
}
```

### Conditional Requests (ETag, Last-Modified)

```kotlin
@GetMapping("/{id}")
fun getUser(
    @PathVariable id: Long,
    request: ServerWebExchange
): ResponseEntity<UserResponse> {
    val user = userService.findById(id)

    // Check ETag
    val etag = "\"${user.version}\""
    if (request.checkNotModified(etag)) {
        return ResponseEntity.status(HttpStatus.NOT_MODIFIED).build()
    }

    return ResponseEntity.ok()
        .eTag(etag)
        .body(user)
}
```

## Request/Response Logging

### Using Filter

```kotlin
@Component
class RequestResponseLoggingFilter : OncePerRequestFilter() {

    override fun doFilterInternal(
        request: HttpServletRequest,
        response: HttpServletResponse,
        filterChain: FilterChain
    ) {
        val wrappedRequest = ContentCachingRequestWrapper(request)
        val wrappedResponse = ContentCachingResponseWrapper(response)

        try {
            filterChain.doFilter(wrappedRequest, wrappedResponse)
        } finally {
            logRequest(wrappedRequest)
            logResponse(wrappedResponse)
            wrappedResponse.copyBodyToResponse()
        }
    }

    private fun logRequest(request: ContentCachingRequestWrapper) {
        val body = String(request.contentAsByteArray, Charsets.UTF_8)
        log.debug("Request: ${request.method} ${request.requestURI}\n$body")
    }

    private fun logResponse(response: ContentCachingResponseWrapper) {
        val body = String(response.contentAsByteArray, Charsets.UTF_8)
        log.debug("Response: ${response.status}\n$body")
    }
}
```

## Content Negotiation

```kotlin
@Configuration
class WebConfig : WebMvcConfigurer {

    override fun configureContentNegotiation(configurer: ContentNegotiationConfigurer) {
        configurer
            .favorParameter(true)
            .parameterName("format")
            .ignoreAcceptHeader(false)
            .defaultContentType(MediaType.APPLICATION_JSON)
            .mediaType("json", MediaType.APPLICATION_JSON)
            .mediaType("xml", MediaType.APPLICATION_XML)
    }
}
```

## WebMVC Anti-Patterns

- Returning entities directly from controllers — use DTOs
- Business logic in controllers — use services
- Catching generic `Exception` in handlers — catch specific exceptions
- Not validating request body — use `@Valid`
- Hardcoding URLs in tests — use `@WebMvcTest` with `MockMvc`
- Not using `ResponseEntity` for status codes — prefer explicit status
- Missing `@ResponseStatus` on exception handlers
- Blocking operations in async controllers without proper configuration