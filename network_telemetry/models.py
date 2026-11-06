from django.db import models


class NetworkAuditLog(models.Model):
    """A filtered syslog event received from network infrastructure."""

    received_at = models.DateTimeField(auto_now_add=True)
    source_address = models.GenericIPAddressField()
    source_port = models.PositiveIntegerField()
    facility = models.PositiveSmallIntegerField(null=True, blank=True)
    severity = models.PositiveSmallIntegerField(null=True, blank=True)
    message = models.TextField()
    event_type = models.CharField(max_length=40, db_index=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.event_type} from {self.source_address}"


class NetworkNodeStatus(models.Model):
    """The latest and historical reachability measurements for a network node."""

    node_address = models.GenericIPAddressField(unique=True)
    node_name = models.CharField(max_length=100, blank=True)
    is_reachable = models.BooleanField()
    latency_ms = models.FloatField(null=True, blank=True)
    checked_at = models.DateTimeField(auto_now=True)
    error_message = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["node_address"]

    def __str__(self):
        return f"{self.node_name or self.node_address}: {'up' if self.is_reachable else 'down'}"
