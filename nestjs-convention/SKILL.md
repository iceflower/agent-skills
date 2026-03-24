---
name: nestjs-convention
description: >-
  NestJS framework conventions and Node.js backend patterns including module
  structure, dependency injection, controllers, services, guards, interceptors,
  pipes, exception filters, Prisma/TypeORM integration, and testing patterns.
  Use when writing or reviewing NestJS applications or Node.js backend code.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# NestJS Conventions

> Based on NestJS 11.x (requires Node.js v20+, Express v5 / Fastify v5).

## 1. Project Structure

### Feature Module Layout

```text
src/
├── app.module.ts
├── main.ts
├── common/               # Shared decorators, filters, guards, interceptors, pipes
├── config/               # Configuration module
└── modules/
    └── user/             # Feature module
        ├── user.module.ts
        ├── user.controller.ts
        ├── user.service.ts
        ├── user.repository.ts
        ├── dto/
        ├── entities/
        └── __tests__/
```

- Group files by feature module, not by technical role
- Keep each module self-contained — own controllers, services, DTOs, and entities
- Place shared cross-cutting concerns in `common/`
- Co-locate tests using `__tests__/` directories or `.spec.ts` suffix

---

## 2. Module System

```typescript
@Module({
  imports: [],                            // Modules this module depends on
  controllers: [UserController],
  providers: [UserService, UserRepository],
  exports: [UserService],                 // Available to importing modules
})
export class UserModule {}
```

### Dynamic Modules

Use `ConfigurableModuleBuilder` for reusable library modules:

```typescript
export const { ConfigurableModuleClass, MODULE_OPTIONS_TOKEN } =
  new ConfigurableModuleBuilder<CacheModuleOptions>()
    .setClassMethodName('forRoot')
    .build();

@Module({})
export class CacheModule extends ConfigurableModuleClass {}
```

### Module Guidelines

- Export only what other modules need — do not export everything
- Use `@Global()` sparingly — only for truly application-wide services (config, logging)
- Prefer `ConfigurableModuleBuilder` over manual `forRoot`/`forRootAsync` boilerplate
- Avoid circular module dependencies — extract shared logic into a separate module

---

## 3. Dependency Injection

### Custom Providers

```typescript
// useValue — static configuration or mock
{ provide: 'API_KEY', useValue: process.env.API_KEY }

// useFactory — dynamic creation with dependencies
{
  provide: 'ASYNC_CONNECTION',
  useFactory: async (config: ConfigService) => createConnection(config.get('db')),
  inject: [ConfigService],
}

// useClass — conditional implementation
{
  provide: LoggerService,
  useClass: process.env.NODE_ENV === 'production' ? ProdLogger : DevLogger,
}
```

### Injection Scopes

| Scope       | Lifetime                      | Use Case                        |
| ----------- | ----------------------------- | ------------------------------- |
| `DEFAULT`   | Singleton (shared across app) | Stateless services (most cases) |
| `REQUEST`   | New instance per request      | Request-scoped state            |
| `TRANSIENT` | New instance per injection    | Stateful, non-shared helpers    |

### DI Guidelines

- Default to `Scope.DEFAULT` (singleton) — most performant
- `REQUEST` scope propagates up the injection chain — every dependent also becomes request-scoped
- Inject via token strings or symbols when swappability is needed
- Use `@Optional()` when a dependency may not be registered

---

## 4. Controllers

```typescript
@Controller('users')
export class UserController {
  constructor(private readonly userService: UserService) {}

  @Post()
  @HttpCode(HttpStatus.CREATED)
  async create(@Body() dto: CreateUserDto): Promise<UserResponseDto> {
    return this.userService.create(dto);
  }

  @Get(':id')
  async findOne(@Param('id', ParseUUIDPipe) id: string): Promise<UserResponseDto> {
    return this.userService.findOne(id);
  }

  @Get()
  async findAll(
    @Query('page', new DefaultValuePipe(1), ParseIntPipe) page: number,
    @Query('limit', new DefaultValuePipe(20), ParseIntPipe) limit: number,
  ): Promise<PaginatedResponse<UserResponseDto>> {
    return this.userService.findAll({ page, limit });
  }
}
```

- Controllers handle HTTP concerns only — delegate business logic to services
- Use explicit `@HttpCode()` for non-GET endpoints when the default 200 is incorrect
- Use built-in pipes (`ParseIntPipe`, `ParseUUIDPipe`, `DefaultValuePipe`) for parameter transformation
- Return DTOs, not entities — never expose database models directly

---

## 5. Services

```typescript
@Injectable()
export class UserService {
  constructor(private readonly userRepository: UserRepository) {}

  async create(dto: CreateUserDto): Promise<UserResponseDto> {
    const existing = await this.userRepository.findByEmail(dto.email);
    if (existing) throw new ConflictException('Email already in use');
    const user = await this.userRepository.create(dto);
    return UserResponseDto.from(user);
  }

  async findOne(id: string): Promise<UserResponseDto> {
    const user = await this.userRepository.findById(id);
    if (!user) throw new NotFoundException(`User #${id} not found`);
    return UserResponseDto.from(user);
  }
}
```

- Services contain business logic — keep independent of HTTP layer
- Throw NestJS built-in exceptions (`NotFoundException`, `ConflictException`) from services
- Use the repository pattern to abstract data access
- Services should be stateless when using the default singleton scope

---

## 6. Guards, Interceptors, and Pipes

### Execution Order

```text
Middleware → Guards → Interceptors (pre) → Pipes → Handler → Interceptors (post) → Exception Filters
```

### Guard Example (Authorization)

```typescript
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private readonly reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const roles = this.reflector.getAllAndOverride<Role[]>(ROLES_KEY, [
      context.getHandler(), context.getClass(),
    ]);
    if (!roles) return true;
    const user = context.switchToHttp().getRequest().user;
    return roles.some((role) => user.roles?.includes(role));
  }
}
```

### Interceptor Example (Response Wrapping)

```typescript
@Injectable()
export class TransformInterceptor<T> implements NestInterceptor<T, ResponseWrapper<T>> {
  intercept(context: ExecutionContext, next: CallHandler): Observable<ResponseWrapper<T>> {
    return next.handle().pipe(
      map((data) => ({ success: true, data, timestamp: new Date().toISOString() })),
    );
  }
}
```

### Binding Levels

| Level      | Method                                   | Scope                |
| ---------- | ---------------------------------------- | -------------------- |
| Global     | `app.useGlobalGuards(new Guard())`       | All routes           |
| Global DI  | `APP_GUARD` / `APP_INTERCEPTOR` provider | All routes (with DI) |
| Controller | `@UseGuards(Guard)` on class             | All class methods    |
| Method     | `@UseGuards(Guard)` on method            | Single endpoint      |

### Middleware Guidelines

- Register global guards/interceptors/pipes via `APP_*` tokens for DI support
- Guards decide access — return `true`/`false` or throw `UnauthorizedException`
- Interceptors wrap execution — ideal for response mapping, logging, caching
- Pipes transform or validate input before it reaches the handler

---

## 7. Exception Filters

### Built-in Exceptions

| Exception                        | Status Code |
| -------------------------------- | ----------- |
| `BadRequestException`            | 400         |
| `UnauthorizedException`          | 401         |
| `ForbiddenException`             | 403         |
| `NotFoundException`              | 404         |
| `ConflictException`              | 409         |
| `UnprocessableEntityException`   | 422         |
| `InternalServerErrorException`   | 500         |

### Exception Filter Guidelines

- Use built-in HTTP exceptions for standard cases
- Create domain-specific exceptions extending `HttpException` for business errors
- Implement a global `@Catch()` filter (`ExceptionFilter`) to standardize error response format
- Never expose stack traces or internal details in production responses

---

## 8. Data Access

### Prisma Integration

```typescript
@Injectable()
export class PrismaService extends PrismaClient implements OnModuleInit {
  async onModuleInit(): Promise<void> { await this.$connect(); }
}

@Injectable()
export class UserRepository {
  constructor(private readonly prisma: PrismaService) {}

  async findById(id: string): Promise<User | null> {
    return this.prisma.user.findUnique({ where: { id } });
  }

  async create(data: CreateUserDto): Promise<User> {
    return this.prisma.user.create({ data });
  }
}
```

### Prisma vs TypeORM

| Aspect            | Prisma                       | TypeORM                      |
| ----------------- | ---------------------------- | ---------------------------- |
| Schema definition | `.prisma` file (SDL)         | TypeScript decorators        |
| Migrations        | `prisma migrate`             | TypeORM CLI                  |
| Type safety       | Generated client (excellent) | Partial (runtime decorators) |
| Relations         | Explicit include/select      | Eager/lazy loading options   |
| Raw queries       | `$queryRaw`                  | `query()` / QueryBuilder     |

### Data Access Guidelines

- Wrap Prisma/TypeORM behind a repository layer for testability
- Use transactions (`$transaction` / `EntityManager`) for multi-step writes
- Prefer Prisma `select` / `include` to avoid over-fetching
- Never expose ORM entities directly — map to response DTOs

---

## 9. Validation

### Global ValidationPipe

```typescript
// main.ts
app.useGlobalPipes(new ValidationPipe({
  whitelist: true,            // Strip non-decorated properties
  forbidNonWhitelisted: true, // Throw on extra properties
  transform: true,            // Auto-transform payloads to DTO classes
}));
```

### DTO Pattern

```typescript
export class CreateUserDto {
  @IsString() @MinLength(2) @MaxLength(50)
  name: string;

  @IsEmail()
  email: string;

  @IsEnum(UserRole)
  role: UserRole;
}

export class UpdateUserDto extends PartialType(CreateUserDto) {}

// Nested validation
export class CreateOrderDto {
  @ValidateNested({ each: true })
  @Type(() => OrderItemDto)
  items: OrderItemDto[];
}
```

- Enable `whitelist` and `forbidNonWhitelisted` globally to reject unexpected fields
- Use `PartialType()`, `PickType()`, `OmitType()` from `@nestjs/mapped-types` to derive DTOs
- Use `@Type()` from `class-transformer` for nested object validation
- Keep DTOs in dedicated `dto/` files — do not mix with entities

---

## 10. Configuration

### Environment Validation

```typescript
import { plainToInstance } from 'class-transformer';
import { IsNumber, IsString, validateSync } from 'class-validator';

class EnvironmentVariables {
  @IsNumber() PORT: number;
  @IsString() DATABASE_URL: string;
  @IsString() JWT_SECRET: string;
}

export function validate(config: Record<string, unknown>) {
  const validated = plainToInstance(EnvironmentVariables, config,
    { enableImplicitConversion: true });
  const errors = validateSync(validated, { skipMissingProperties: false });
  if (errors.length > 0) throw new Error(errors.toString());
  return validated;
}

// app.module.ts
@Module({
  imports: [ConfigModule.forRoot({ isGlobal: true, validate })],
})
export class AppModule {}
```

### Type-Safe Access

```typescript
// Use getOrThrow() to fail fast on missing config
const secret = this.configService.getOrThrow<string>('JWT_SECRET');
```

- Always validate environment variables at startup — fail fast on missing config
- Use `ConfigModule.forRoot({ isGlobal: true })` to avoid importing in every module
- Use `getOrThrow()` instead of `get()` to catch missing config at runtime
- Never hardcode secrets — use environment variables or external secret managers

---

## 11. Testing

### Unit Test

```typescript
describe('UserService', () => {
  let service: UserService;
  let repository: jest.Mocked<UserRepository>;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      providers: [
        UserService,
        { provide: UserRepository, useValue: { findById: jest.fn(), create: jest.fn() } },
      ],
    }).compile();
    service = module.get(UserService);
    repository = module.get(UserRepository);
  });

  it('should throw NotFoundException when user not found', async () => {
    repository.findById.mockResolvedValue(null);
    await expect(service.findOne('1')).rejects.toThrow(NotFoundException);
  });
});
```

### E2E Test

```typescript
describe('UserController (e2e)', () => {
  let app: INestApplication;

  beforeAll(async () => {
    const module = await Test.createTestingModule({ imports: [AppModule] }).compile();
    app = module.createNestApplication();
    app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }));
    await app.init();
  });

  afterAll(() => app.close());

  it('POST /users should create a user', () =>
    request(app.getHttpServer())
      .post('/users')
      .send({ name: 'John', email: 'john@test.com', role: 'user' })
      .expect(201));
});
```

### Testing Guidelines

- Use `Test.createTestingModule()` for all NestJS tests
- Mock dependencies at the provider level, not with manual class mocks
- In e2e tests, replicate the same global pipes/guards/filters as `main.ts`
- Test behavior (input/output), not implementation details
- Use `overrideProvider()` / `overrideGuard()` for selective test overrides

---

## 12. Anti-Patterns

### Module and DI Anti-Patterns

- Overusing `@Global()` — makes dependency graph implicit and hard to trace
- Circular module dependencies — extract shared logic into a common module
- Using `REQUEST` scope unnecessarily — propagates to entire dependency chain
- Registering everything in `AppModule` instead of feature modules

### Controller and Service Anti-Patterns

- Putting business logic in controllers — delegate to services
- Returning ORM entities directly — always map to response DTOs
- Catching exceptions manually instead of using exception filters
- Using `@Res()` decorator — bypasses NestJS response handling (use only for streaming)

### Infrastructure Anti-Patterns

- Registering global middleware with `app.useGlobal*()` instead of `APP_*` tokens — loses DI
- Calling Prisma/TypeORM directly in controllers — use repository or service layer
- Missing `$transaction` for multi-step writes
- Not validating environment variables at startup — causes runtime crashes
- Not applying global pipes/filters in e2e test setup — diverges from production behavior

---

## 13. Related Skills

- **typescript-convention**: TypeScript type system and coding patterns
- **api-design**: REST API design principles and response conventions
- **testing**: General testing strategies and patterns
- **security**: Authentication, authorization, and secure coding practices
- **error-handling**: Error classification and handling patterns

## 14. Additional References

- [NestJS Official Documentation](https://docs.nestjs.com/) — Comprehensive framework guide
- [NestJS GitHub Repository](https://github.com/nestjs/nest) — Source code and release notes
- [Prisma with NestJS](https://docs.nestjs.com/recipes/prisma) — Official Prisma integration recipe
- [NestJS Migration Guide](https://docs.nestjs.com/migration-guide) — Version migration instructions
