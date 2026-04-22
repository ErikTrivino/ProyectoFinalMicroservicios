package co.edu.uniquindio.ingesis.security;

import jakarta.ws.rs.core.SecurityContext;
import java.security.Principal;

public class AuthSecurityContext implements SecurityContext {

    private final String userEmail;
    private final String userRole;
    private final boolean secure;

    public AuthSecurityContext(String userEmail, String userRole, boolean secure) {
        this.userEmail = userEmail;
        this.userRole = userRole;
        this.secure = secure;
    }

    @Override
    public Principal getUserPrincipal() {
        return () -> userEmail; // Devuelve el email como identificación
    }

    @Override
    public boolean isUserInRole(String role) {
        return userRole.equals(role); // Compara el rol del usuario con el rol solicitado
    }

    @Override
    public boolean isSecure() {
        return secure;
    }

    @Override
    public String getAuthenticationScheme() {
        return "Bearer";
    }
}
