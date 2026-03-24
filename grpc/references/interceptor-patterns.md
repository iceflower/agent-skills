# gRPC Interceptor Patterns

## Server Interceptor Example (Kotlin)

```kotlin
class AuthenticationInterceptor(
    private val tokenValidator: TokenValidator
) : ServerInterceptor {

    override fun <ReqT, RespT> interceptCall(
        call: ServerCall<ReqT, RespT>,
        headers: Metadata,
        next: ServerCallHandler<ReqT, RespT>
    ): ServerCall.Listener<ReqT> {
        val token = headers.get(AUTH_METADATA_KEY)

        if (token == null) {
            call.close(
                Status.UNAUTHENTICATED.withDescription("Missing authentication token"),
                Metadata()
            )
            return object : ServerCall.Listener<ReqT>() {}
        }

        val principal = tokenValidator.validate(token)
            ?: run {
                call.close(
                    Status.UNAUTHENTICATED.withDescription("Invalid authentication token"),
                    Metadata()
                )
                return object : ServerCall.Listener<ReqT>() {}
            }

        val context = Context.current().withValue(PRINCIPAL_CONTEXT_KEY, principal)
        return Contexts.interceptCall(context, call, headers, next)
    }

    companion object {
        val AUTH_METADATA_KEY: Metadata.Key<String> =
            Metadata.Key.of("authorization", Metadata.ASCII_STRING_MARSHALLER)
        val PRINCIPAL_CONTEXT_KEY: Context.Key<Principal> =
            Context.key("principal")
    }
}
```

## Client Interceptor Example (Kotlin)

```kotlin
class DeadlinePropagationInterceptor(
    private val defaultDeadlineMs: Long = 5000
) : ClientInterceptor {

    override fun <ReqT, RespT> interceptCall(
        method: MethodDescriptor<ReqT, RespT>,
        callOptions: CallOptions,
        next: Channel
    ): ClientCall<ReqT, RespT> {
        val options = if (callOptions.deadline == null) {
            callOptions.withDeadlineAfter(defaultDeadlineMs, TimeUnit.MILLISECONDS)
        } else {
            callOptions
        }
        return next.newCall(method, options)
    }
}
```
