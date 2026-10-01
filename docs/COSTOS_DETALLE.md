# Costos AWS detallados

Consulta: **1 de octubre de 2026**. USD/mes, sin IVA, soporte, dominio ni mano de obra; no se aplican créditos promocionales. Cada alternativa reside íntegramente en una sola región.

## Opción recomendada: todo en `us-east-1`

| Servicio | Tarifa unitaria verificada | Fuente oficial |
|---|---:|---|
| Lightsail Linux: 4 GB, 2 vCPU, 80 GB SSD, IPv4 y 4 TB | 24.00/mes | [Lightsail](https://aws.amazon.com/lightsail/pricing/) |
| Snapshot Lightsail | 0.05/GB-mes | [Lightsail snapshots](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-faq-snapshots.html) |
| Fargate Linux x86 | 0.04048/vCPU-h + 0.004445/GB-h | [Fargate](https://aws.amazon.com/fargate/pricing/) |
| S3 Standard / PUT / GET | 0.023/GB-mes; 0.005/1k; 0.0004/1k | [S3](https://aws.amazon.com/s3/pricing/) |
| Athena | 5/TB escaneado | [Athena](https://aws.amazon.com/athena/pricing/) |
| Lambda x86 | 0.20/millón de solicitudes + 0.0000166667/GB-s | [Lambda](https://aws.amazon.com/lambda/pricing/) |
| Secrets Manager | 0.40/secreto-mes + 0.05/10k llamadas | [Secrets Manager](https://aws.amazon.com/secrets-manager/pricing/) |
| IPv4 pública | 0.005/h | [VPC](https://aws.amazon.com/vpc/pricing/) |
| QuickSight Author / Reader | 24 / 3 por usuario-mes | [QuickSight](https://aws.amazon.com/quick/quicksight/pricing/) |

**Cálculo esperado:** plataforma de datos USD 4.99 + Lightsail USD 24 + 20 GB snapshot × 0.05 = **USD 29.99**; contingencia 15% = **USD 4.50**; total = **USD 34.49**; margen contra USD 200 = **USD 165.51**. Superset, Redis, metadatos y proxy comparten la instancia; licencia Superset = USD 0.

## Alternativa de residencia: todo en `mx-central-1`

| Servicio | Tarifa unitaria verificada | Fuente oficial |
|---|---:|---|
| EC2 Linux `t4g.medium` | 0.0353/h | [AWS Price List API, publicación 25-sep-2026](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/region_index.json) |
| Fargate Linux x86 | 0.042504/vCPU-h + 0.00466725/GB-h | [AWS Price List API, publicación 11-sep-2026](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/region_index.json) |
| EBS gp3 | 0.084/GB-mes | [AWS Price List API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/region_index.json) |
| Snapshot EBS | 0.053/GB-mes | [AWS Price List API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/region_index.json) |
| IPv4 pública | 0.005/h | [VPC](https://aws.amazon.com/vpc/pricing/) |

**EC2 Superset:** 730 h × 0.0353 = 25.77; gp3 80 GB × 0.084 = 6.72; IPv4 730 h × 0.005 = 3.65; snapshot 20 GB × 0.053 = 1.06; total = **USD 37.20**. Plataforma de datos regional = **USD 5.00** (mismos volúmenes; Fargate regional incrementa USD 0.01): subtotal **USD 42.20**; contingencia 15% = **USD 6.33**; total = **USD 48.53**; margen = **USD 151.47**. S3, Lambda, Athena y Glue deben reconfirmarse en la calculadora antes de contratar; cualquier diferencia queda marcada **por confirmar**, no como precio inventado.

Lightsail no está disponible en México Central: [regiones oficiales de Lightsail](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-regions-and-availability-zones-in-amazon-lightsail.html). Por eso no se mezcla: residencia nacional implica EC2 y todos los servicios en `mx-central-1`.

## Comparaciones y supuestos

- QuickSight 1 autor + 5 lectores: 24 + 5 × 3 = **USD 39/mes**. Con 40 lectores: 24 + 40 × 3 = **USD 144/mes**. No se activan usuarios Pro ni Q&A.
- AWS Transfer SFTP: 0.30/h (≈USD 216/mes) + 0.04/GB ([fuente](https://aws.amazon.com/aws-transfer-family/pricing/)); se prefiere exportación diaria POS/ERP mediante HTTPS a S3.
- OAuth Google/Microsoft y Let's Encrypt no tienen cargo AWS directo. Los snapshots presupuestan 20 GB; PostgreSQL de metadatos también requiere backup lógico a S3.
