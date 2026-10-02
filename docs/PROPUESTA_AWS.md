# Propuesta AWS para CaféNorte

## Carta al dueño y a TI

CaféNorte necesita un número confiable de ventas e inventario, con trazabilidad desde POS,
ERP y Shopify. Propongo una plataforma batch diaria, dentro del presupuesto aproximado de
USD 200/mes, que conserva los originales, excluye PII analítica y hace visible cada rechazo.

## Arquitectura propuesta

```text
POS/ERP -- HTTPS --> S3 Bronze inmutable --> ECS/Fargate + Polars --> S3 Silver
Shopify -- Lambda --> S3 Bronze                              --> Glue Catalog
EventBridge -> Step Functions -> dbt -> S3 Gold -> Athena -> Superset
Secrets Manager -> Lambda/Superset       CloudWatch + CloudTrail -> operación
```

S3 es el histórico barato e inmutable; Lambda recibe Shopify y ECS ejecuta el batch sin
servidores permanentes; Glue registra esquema; Athena consulta Gold; dbt conserva semántica
y reconciliación; Superset entrega las cuatro vistas con RLS. Secrets Manager evita secretos
en imágenes. Todo se ubica en `us-east-1` para no pagar transferencia entre regiones. Si
Jurídico exige residencia nacional, despliego todo en la región mexicana disponible y cambio
Lightsail por EC2 con rol IAM.

## Costo mensual

Supuestos: 80k filas POS/mes, inventario diario de 40 tiendas, 1k pedidos Shopify/mes,
una corrida diaria y 0.10 TB escaneados. Sin IVA, soporte ni horas operativas.

| Concepto | Esperado |
|---|---:|
| Ingesta, secretos y procesamiento | USD 1.08 |
| S3, Athena, ECR y Glue | USD 1.34 |
| Seguridad, logs y dev/test | USD 2.57 |
| Superset en Lightsail 4 GB + snapshots | USD 25.00 |
| Subtotal | USD 29.99 |
| Contingencia 15% | USD 4.50 |
| **Total** | **USD 34.49/mes** |

La estimación deja USD 165.51 bajo el límite de USD 200. El detalle de fórmulas está en
[`COSTOS_DETALLE.md`](COSTOS_DETALLE.md). QuickSight evita operar Superset, pero el costo
crece por lector; SFTP administrado superaría el presupuesto por sí solo, por eso prefiero
HTTPS a S3 mientras el proveedor valida sus capacidades.

## Fases, riesgos y controles

| Fase | Entrega | Riesgo y control |
|---|---|---|
| 1 | Contratos, S3 Bronze, secretos e ingesta | Exportación real del legacy; prueba de muestra y cuarentena |
| 2 | Silver, PII, dbt y reconciliación | Costos/devoluciones; conciliación centavo a centavo |
| 3 | Gold, Superset, OAuth/RLS y dashboards | RLS probado con datos reales |
| 4 | Backup, alertas, FinOps y recuperación | Instancia única; snapshots + dump lógico a S3 |

La primera versión productiva no promete alta disponibilidad: Lightsail es una instancia única.
Se escala a 8 GB o se separan metadatos si CPU/memoria supera 70% sostenido, p95 supera 10 s
o las pruebas con 40 usuarios fallan. CloudWatch y CloudTrail cubren operación y auditoría;
OAuth y HTTPS reemplazan las credenciales locales del demo.

## Supuestos y preguntas abiertas antes de firmar

- ¿POS y ERP pueden exportar diariamente CSV/JSON y subirlos por HTTPS?
- ¿`tiendas_info` es el maestro aunque incluya ciudades y regiones no mencionadas?
- ¿Cuál es la política de retención y está autorizado procesar los campos de Shopify?
- ¿Qué reglas aplican a devoluciones, impuestos, costos y cambios de proveedor?
- ¿Google o Microsoft será el IdP, y quién operará parches, backups y respuesta a incidentes?
- ¿Se confirma `us-east-1` o exige Jurídico una región mexicana?

La primera entrega debe ser contratos + Bronze + seguridad; después Silver/Gold y finalmente
el visor. Así se puede demostrar calidad antes de pagar una plataforma de BI.
