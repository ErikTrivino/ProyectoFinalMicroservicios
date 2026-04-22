package co.edu.uniquindio.ingesis.security;

import io.jsonwebtoken.Claims;
import jakarta.annotation.Priority;
import jakarta.inject.Inject;
import jakarta.ws.rs.Priorities;
import jakarta.ws.rs.container.ContainerRequestContext;
import jakarta.ws.rs.container.ContainerRequestFilter;
import jakarta.ws.rs.core.PathSegment;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.core.SecurityContext;
import jakarta.ws.rs.ext.Provider;

import java.io.IOException;
import java.util.List;

@Provider
@Priority(Priorities.AUTHENTICATION)
public class JWTAuthFilter implements ContainerRequestFilter {

    @Inject JWTUtil jwtUtil;

    @Override
    public void filter(ContainerRequestContext requestContext) throws IOException {
        List<PathSegment> segments = requestContext.getUriInfo().getPathSegments();
        String first  = segments.isEmpty()  ? "" : segments.get(0).getPath();
        String second = segments.size() > 1 ? segments.get(1).getPath() : "";
        String method = requestContext.getMethod();

        // Única ruta pública: POST /auth/login
        if ("auth".equals(first) && "login".equals(second) && "POST".equals(method)) {
            return;
        }

        String header = requestContext.getHeaderString("Authorization");
        if (header == null || !header.startsWith("Bearer ")) {
            abort(requestContext, "Token no proporcionado o inválido");
            return;
        }

        try {
            Claims claims = jwtUtil.validateToken(header.substring(7));
            String email  = claims.getSubject();
            String role   = claims.get("rol", String.class);
            final SecurityContext current = requestContext.getSecurityContext();
            requestContext.setSecurityContext(
                    new AuthSecurityContext(email, role, current.isSecure()));
        } catch (Exception e) {
            abort(requestContext, "Token inválido o expirado");
        }
    }

    private void abort(ContainerRequestContext ctx, String mensaje) {
        ctx.abortWith(Response.status(Response.Status.UNAUTHORIZED)
                .entity("{\"status\":401,\"error\":\"Unauthorized\",\"mensaje\":\"" + mensaje + "\"}")
                .build());
    }
}
