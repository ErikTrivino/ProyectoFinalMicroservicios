package co.edu.uniquindio.ingesis.security;

import io.smallrye.jwt.build.Jwt;
import jakarta.enterprise.context.ApplicationScoped;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.time.Duration;

/**
 * Generador de tokens JWT usando SmallRye JWT de Quarkus.
 * La validacion del token la hace Quarkus automaticamente —
 * ya no necesitamos JWTAuthFilter ni AuthSecurityContext.
 */
@ApplicationScoped
public class JWTUtil {

    @ConfigProperty(name = "mp.jwt.verify.issuer")
    String issuer;

    @ConfigProperty(name = "jwt.expiration", defaultValue = "86400")
    long expirationSeconds;

    /**
     * Genera un token JWT firmado con la clave privada configurada.
     *
     * @param email email del usuario (subject)
     * @param rol   rol del usuario: ADMIN | USER | EMPLEADO
     * @return token JWT firmado
     */
    public String generateToken(String email, String rol) {
        return Jwt.issuer(issuer)
                .subject(email)
                .groups(rol)                          // SmallRye usa "groups" para roles
                .expiresIn(Duration.ofSeconds(expirationSeconds))
                .sign();                              // firma con la clave privada del keystore
    }
}
