using Microsoft.EntityFrameworkCore;
using NotificacionesService.Models;

namespace NotificacionesService.Data;

public class NotificacionesDbContext : DbContext
{
    public NotificacionesDbContext(DbContextOptions<NotificacionesDbContext> options)
        : base(options)
    {
    }

    public DbSet<Notificacion> Notificaciones { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<Notificacion>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasMaxLength(36);
            entity.HasIndex(e => e.EmpleadoId);
        });
    }
}
